//! Various utitlity functions and data structures

use datafusion::physical_plan::metrics::MetricsSet;

pub mod once_async;

pub fn write_metrics_as_json(
    metrics: &Option<MetricsSet>,
    output: &mut String,
) -> std::fmt::Result {
    use std::fmt::Write;

    write!(output, ", \"metrics\": [")?;

    let mut first = true;

    if let Some(metrics) = metrics {
        for metric in metrics.iter() {
            if !first {
                write!(output, ",")?;
            }
            write!(
                output,
                "{{ \"name\":\"{}\", \"value\": {} ",
                metric.value().name(),
                metric.value().as_usize()
            )?;
            if let Some(partition) = metric.partition() {
                write!(output, ", \"partition\": {}", partition)?;
            }
            write!(output, "}}")?;
            first = false;
        }
    }
    write!(output, "]")?;
    Ok(())
}
