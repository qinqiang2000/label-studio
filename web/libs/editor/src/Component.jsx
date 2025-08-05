import { Component } from "react";
import App from "./components/App/App";
import { configureStore } from "./configureStore";

export class LabelStudio extends Component {
  state = {
    initialized: false,
  };

  componentDidMount() {
    configureStore(this.props).then(({ store }) => {
      this.store = store;
      window.Htx = this.store;
      this._patchTaskDataWithAnnotation(this.props.task);
      this.setState({ initialized: true });
    });
  }

  componentDidUpdate(prevProps) {
    if (this.props.task !== prevProps.task) {
      this.store.resetState();
      this._patchTaskDataWithAnnotation(this.props.task);
      this.store.assignTask(this.props.task);
      this.store.initializeStore(this.props.task);
    }
  }

  /**
   * 优先用 annotation.result 里的 textarea 内容（如 invoices_json）填充 data
   * 没有 annotation 时，用 prediction.result
   * 多个 annotation/prediction 时，取最新的（按 created_at/updated_at/id 最大）
   * @param {object} task
   */
  _patchTaskDataWithAnnotation(task) {
    console.log("[patch] called with task:", task);
    if (!task || !task.data) return;
    // 1. 优先最新 annotation
    let source = null;
    if (Array.isArray(task.annotations) && task.annotations.length > 0) {
      console.log("[patch] annotations:", task.annotations);
      source = [...task.annotations]
        .filter((a) => Array.isArray(a.result) && a.result.length > 0)
        .sort((a, b) => {
          const getTime = (x) => new Date(x.updated_at || x.created_at || 0).getTime();
          return getTime(b) - getTime(a) || (b.id || 0) - (a.id || 0);
        })[0];
      console.log("[patch] picked annotation:", source);
    }
    // 2. 没有 annotation 时，fallback 到最新 prediction
    if (!source && Array.isArray(task.predictions) && task.predictions.length > 0) {
      console.log("[patch] predictions:", task.predictions);
      source = [...task.predictions]
        .filter((p) => Array.isArray(p.result) && p.result.length > 0)
        .sort((a, b) => {
          const getTime = (x) => new Date(x.updated_at || x.created_at || 0).getTime();
          return getTime(b) - getTime(a) || (b.id || 0) - (a.id || 0);
        })[0];
      console.log("[patch] picked prediction:", source);
    }
    if (!source) {
      console.log("[patch] no annotation or prediction found");
      return;
    }
    source.result.forEach((r) => {
      if (r.type === "textarea" && r.from_name && r.value && Array.isArray(r.value.text)) {
        const key = r.from_name;
        const val = r.value.text[0];
        if (key && val !== undefined && val !== null) {
          if (!task.data[key] || task.data[key] === "") {
            console.log(`[patch] patching data[${key}] =`, val);
            task.data[key] = val;
          } else {
            console.log(`[patch] skip patch data[${key}], already has value:`, task.data[key]);
          }
        }
      }
    });
  }

  render() {
    return this.state.initialized ? <App store={this.store} /> : null;
  }
}
