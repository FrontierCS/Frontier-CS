//! Extended Implementation of physical plan display to also allows JSON formatting.
//! Implementation based on Datafusion's [DisplayableExecutionPlan].

use std::fmt;

//use datafusion::parquet::arrow::async_reader::MetadataLoader;
use datafusion::physical_plan::{accept, ExecutionPlan, ExecutionPlanVisitor};

use datafusion::common::arrow::datatypes::SchemaRef;
use datafusion::common::display::{GraphvizBuilder, PlanType, StringifiedPlan};
use datafusion::physical_expr::PhysicalSortExpr;

use datafusion::physical_plan::DisplayFormatType;

/// Wraps an `ExecutionPlan` with various ways to display this plan
pub struct ExtDisplayableExecutionPlan<'a> {
    inner: &'a dyn ExecutionPlan,
    /// How to show metrics
    show_metrics: ShowMetrics,
    /// If statistics should be displayed
    show_statistics: bool,
}

impl<'a> ExtDisplayableExecutionPlan<'a> {
    /// Create a wrapper around an [`ExecutionPlan`] which can be
    /// pretty printed in a variety of ways
    pub fn new(inner: &'a dyn ExecutionPlan) -> Self {
        Self {
            inner,
            show_metrics: ShowMetrics::None,
            show_statistics: false,
        }
    }

    /// Create a wrapper around an [`ExecutionPlan`] which can be
    /// pretty printed in a variety of ways that also shows aggregated
    /// metrics
    pub fn with_metrics(inner: &'a dyn ExecutionPlan) -> Self {
        Self {
            inner,
            show_metrics: ShowMetrics::Aggregated,
            show_statistics: false,
        }
    }

    /// Create a wrapper around an [`ExecutionPlan`] which can be
    /// pretty printed in a variety of ways that also shows all low
    /// level metrics
    pub fn with_full_metrics(inner: &'a dyn ExecutionPlan) -> Self {
        Self {
            inner,
            show_metrics: ShowMetrics::Full,
            show_statistics: false,
        }
    }

    /// Enable display of statistics
    pub fn set_show_statistics(mut self, show_statistics: bool) -> Self {
        self.show_statistics = show_statistics;
        self
    }

    /// Return a `format`able structure that produces a single line
    /// per node.
    ///
    /// ```text
    /// ProjectionExec: expr=[a]
    ///   CoalesceBatchesExec: target_batch_size=8192
    ///     FilterExec: a < 5
    ///       RepartitionExec: partitioning=RoundRobinBatch(16)
    ///         CsvExec: source=...",
    /// ```
    pub fn indent(&self, verbose: bool) -> impl fmt::Display + 'a {
        let format_type = if verbose {
            DisplayFormatType::Verbose
        } else {
            DisplayFormatType::Default
        };
        struct Wrapper<'a> {
            format_type: DisplayFormatType,
            plan: &'a dyn ExecutionPlan,
            show_metrics: ShowMetrics,
            show_statistics: bool,
        }
        impl<'a> fmt::Display for Wrapper<'a> {
            fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
                let mut visitor = IndentVisitor {
                    t: self.format_type,
                    f,
                    indent: 0,
                    show_metrics: self.show_metrics,
                    show_statistics: self.show_statistics,
                };
                accept(self.plan, &mut visitor)
            }
        }
        Wrapper {
            format_type,
            plan: self.inner,
            show_metrics: self.show_metrics,
            show_statistics: self.show_statistics,
        }
    }

    /// Returns a `format`able structure that produces graphviz format for execution plan, which can
    /// be directly visualized [here](https://dreampuf.github.io/GraphvizOnline).
    ///
    /// An example is
    /// ```dot
    /// strict digraph dot_plan {
    //     0[label="ProjectionExec: expr=[id@0 + 2 as employee.id + Int32(2)]",tooltip=""]
    //     1[label="EmptyExec",tooltip=""]
    //     0 -> 1
    // }
    /// ```
    pub fn graphviz(&self) -> impl fmt::Display + 'a {
        struct Wrapper<'a> {
            plan: &'a dyn ExecutionPlan,
            show_metrics: ShowMetrics,
            show_statistics: bool,
        }
        impl<'a> fmt::Display for Wrapper<'a> {
            fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
                let t = DisplayFormatType::Default;

                let mut visitor = GraphvizVisitor {
                    f,
                    t,
                    show_metrics: self.show_metrics,
                    show_statistics: self.show_statistics,
                    graphviz_builder: GraphvizBuilder::default(),
                    parents: Vec::new(),
                };

                visitor.start_graph()?;

                accept(self.plan, &mut visitor)?;

                visitor.end_graph()?;
                Ok(())
            }
        }

        Wrapper {
            plan: self.inner,
            show_metrics: self.show_metrics,
            show_statistics: self.show_statistics,
        }
    }

    /// Returns a `format`able structure that produces json format for execution plan.
    ///
    /// An example is
    /// TODO
    /// ```
    pub fn json(&self, verbose: bool) -> impl fmt::Display + 'a {
        let format_type = if verbose {
            DisplayFormatType::Verbose
        } else {
            DisplayFormatType::Default
        };
        struct Wrapper<'a> {
            format_type: DisplayFormatType,
            plan: &'a dyn ExecutionPlan,
            show_metrics: ShowMetrics,
            show_statistics: bool,
        }
        impl<'a> fmt::Display for Wrapper<'a> {
            fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
                let mut visitor = JsonVisitor {
                    t: self.format_type,
                    f,
                    show_metrics: self.show_metrics,
                    show_statistics: self.show_statistics,
                    comma_stack: vec![false],
                };
                accept(self.plan, &mut visitor)
            }
        }
        Wrapper {
            format_type,
            plan: self.inner,
            show_metrics: self.show_metrics,
            show_statistics: self.show_statistics,
        }
    }

    /// Return a single-line summary of the root of the plan
    /// Example: `ProjectionExec: expr=[a@0 as a]`.
    pub fn one_line(&self) -> impl fmt::Display + 'a {
        struct Wrapper<'a> {
            plan: &'a dyn ExecutionPlan,
            show_metrics: ShowMetrics,
            show_statistics: bool,
        }

        impl<'a> fmt::Display for Wrapper<'a> {
            fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
                let mut visitor = IndentVisitor {
                    f,
                    t: DisplayFormatType::Default,
                    indent: 0,
                    show_metrics: self.show_metrics,
                    show_statistics: self.show_statistics,
                };
                visitor.pre_visit(self.plan)?;
                Ok(())
            }
        }

        Wrapper {
            plan: self.inner,
            show_metrics: self.show_metrics,
            show_statistics: self.show_statistics,
        }
    }

    /// format as a `StringifiedPlan`
    pub fn to_stringified(&self, verbose: bool, plan_type: PlanType) -> StringifiedPlan {
        StringifiedPlan::new(plan_type, self.indent(verbose).to_string())
    }
}

#[derive(Debug, Clone, Copy)]
enum ShowMetrics {
    /// Do not show any metrics
    None,

    /// Show aggregrated metrics across partition
    Aggregated,

    /// Show full per-partition metrics
    Full,
}

/// Formats plans with a single line per node.
struct IndentVisitor<'a, 'b> {
    /// How to format each node
    t: DisplayFormatType,
    /// Write to this formatter
    f: &'a mut fmt::Formatter<'b>,
    /// Indent size
    indent: usize,
    /// How to show metrics
    show_metrics: ShowMetrics,
    /// If statistics should be displayed
    show_statistics: bool,
}

impl<'a, 'b> ExecutionPlanVisitor for IndentVisitor<'a, 'b> {
    type Error = fmt::Error;
    fn pre_visit(&mut self, plan: &dyn ExecutionPlan) -> Result<bool, Self::Error> {
        write!(self.f, "{:indent$}", "", indent = self.indent * 2)?;
        plan.fmt_as(self.t, self.f)?;
        match self.show_metrics {
            ShowMetrics::None => {}
            ShowMetrics::Aggregated => {
                if let Some(metrics) = plan.metrics() {
                    let metrics = metrics
                        .aggregate_by_name()
                        .sorted_for_display()
                        .timestamps_removed();

                    write!(self.f, ", metrics=[{metrics}]")?;
                } else {
                    write!(self.f, ", metrics=[]")?;
                }
            }
            ShowMetrics::Full => {
                if let Some(metrics) = plan.metrics() {
                    write!(self.f, ", metrics=[{metrics}]")?;
                } else {
                    write!(self.f, ", metrics=[]")?;
                }
            }
        }
        if self.show_statistics {
            let stats = plan.statistics().map_err(|_e| fmt::Error)?;
            write!(self.f, ", statistics=[{}]", stats)?;
        }
        writeln!(self.f)?;
        self.indent += 1;
        Ok(true)
    }

    fn post_visit(&mut self, _plan: &dyn ExecutionPlan) -> Result<bool, Self::Error> {
        self.indent -= 1;
        Ok(true)
    }
}

/// Formats plans with a single line per node.
struct JsonVisitor<'a, 'b> {
    /// How to format the operator for each node
    t: DisplayFormatType,
    /// Write to this formatter
    f: &'a mut fmt::Formatter<'b>,
    /// How to show metrics
    show_metrics: ShowMetrics,
    /// If statistics should be displayed
    show_statistics: bool,
    /// Stack that keept strack per level whether we should use a comma to separate the next sibling or not
    comma_stack: Vec<bool>,
}

impl<'a, 'b> ExecutionPlanVisitor for JsonVisitor<'a, 'b> {
    type Error = fmt::Error;
    fn pre_visit(&mut self, plan: &dyn ExecutionPlan) -> Result<bool, Self::Error> {
        // If the top element on the stack is true, we are a second child or later and we need to write a comma
        if let Some(true) = self.comma_stack.last() {
            write!(self.f, ",")?;
        }

        // Open record for current operator
        write!(self.f, "{{")?;

        // Write operator name
        // TODO: in later version of datafusion we should be able to call plan.name() to get the operator name
        write!(self.f, "\"operator\": \"")?;
        plan.fmt_as(self.t, self.f)?;
        write!(self.f, "\"")?;

        // Write metrics
        write!(self.f, ", \"metrics\": [")?;
        let metrics = match self.show_metrics {
            ShowMetrics::None => None,
            ShowMetrics::Aggregated => plan.metrics().map(|metrics| {
                metrics
                    .aggregate_by_name()
                    .sorted_for_display()
                    .timestamps_removed()
            }),
            ShowMetrics::Full => plan.metrics(),
        };

        let mut first = true;

        if let Some(metrics) = metrics {
            for metric in metrics.iter() {
                if !first {
                    write!(self.f, ",")?;
                }
                write!(
                    self.f,
                    "{{ \"name\":\"{}\", \"value\": {} ",
                    metric.value().name(),
                    metric.value().as_usize()
                )?;
                if let Some(partition) = metric.partition() {
                    write!(self.f, ", \"partition\": {}", partition)?;
                }
                write!(self.f, "}}")?;
                first = false;
            }
        }
        write!(self.f, "]")?;

        if self.show_statistics {
            let stats = plan.statistics().map_err(|_e| fmt::Error)?;
            write!(self.f, ", \"statistics\":[{}]", stats)?;
        }

        write!(self.f, ", \"children\": [")?;

        // First child should not add a comma
        self.comma_stack.push(false);

        Ok(true)
    }

    fn post_visit(&mut self, _plan: &dyn ExecutionPlan) -> Result<bool, Self::Error> {
        // Close children array
        write!(self.f, "]")?;
        // Close record for current operator
        write!(self.f, "}}")?;

        // Pop the comma-stack value for the children
        self.comma_stack.pop();

        // make sure that next operators are this level get written with a comma
        self.comma_stack.last_mut().map(|x| *x = true);

        Ok(true)
    }
}

struct GraphvizVisitor<'a, 'b> {
    f: &'a mut fmt::Formatter<'b>,
    /// How to format each node
    t: DisplayFormatType,
    /// How to show metrics
    show_metrics: ShowMetrics,
    /// If statistics should be displayed
    show_statistics: bool,

    graphviz_builder: GraphvizBuilder,
    /// Used to record parent node ids when visiting a plan.
    parents: Vec<usize>,
}

impl GraphvizVisitor<'_, '_> {
    fn start_graph(&mut self) -> fmt::Result {
        self.graphviz_builder.start_graph(self.f)
    }

    fn end_graph(&mut self) -> fmt::Result {
        self.graphviz_builder.end_graph(self.f)
    }
}

impl ExecutionPlanVisitor for GraphvizVisitor<'_, '_> {
    type Error = fmt::Error;

    fn pre_visit(
        &mut self,
        plan: &dyn ExecutionPlan,
    ) -> datafusion::common::Result<bool, Self::Error> {
        let id = self.graphviz_builder.next_id();

        struct Wrapper<'a>(&'a dyn ExecutionPlan, DisplayFormatType);

        impl<'a> std::fmt::Display for Wrapper<'a> {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
                self.0.fmt_as(self.1, f)
            }
        }

        let label = { format!("{}", Wrapper(plan, self.t)) };

        let metrics = match self.show_metrics {
            ShowMetrics::None => "".to_string(),
            ShowMetrics::Aggregated => {
                if let Some(metrics) = plan.metrics() {
                    let metrics = metrics
                        .aggregate_by_name()
                        .sorted_for_display()
                        .timestamps_removed();

                    format!("metrics=[{metrics}]")
                } else {
                    "metrics=[]".to_string()
                }
            }
            ShowMetrics::Full => {
                if let Some(metrics) = plan.metrics() {
                    format!("metrics=[{metrics}]")
                } else {
                    "metrics=[]".to_string()
                }
            }
        };

        let statistics = if self.show_statistics {
            let stats = plan.statistics().map_err(|_e| fmt::Error)?;
            format!("statistics=[{}]", stats)
        } else {
            "".to_string()
        };

        let delimiter = if !metrics.is_empty() && !statistics.is_empty() {
            ", "
        } else {
            ""
        };

        self.graphviz_builder.add_node(
            self.f,
            id,
            &label,
            Some(&format!("{}{}{}", metrics, delimiter, statistics)),
        )?;

        if let Some(parent_node_id) = self.parents.last() {
            self.graphviz_builder
                .add_edge(self.f, *parent_node_id, id)?;
        }

        self.parents.push(id);

        Ok(true)
    }

    fn post_visit(&mut self, _plan: &dyn ExecutionPlan) -> Result<bool, Self::Error> {
        self.parents.pop();
        Ok(true)
    }
}

/// Trait for types which could have additional details when formatted in `Verbose` mode
pub trait DisplayAs {
    /// Format according to `DisplayFormatType`, used when verbose representation looks
    /// different from the default one
    ///
    /// Should not include a newline
    fn fmt_as(&self, t: DisplayFormatType, f: &mut fmt::Formatter) -> fmt::Result;
}

/// A newtype wrapper to display `T` implementing`DisplayAs` using the `Default` mode
pub struct DefaultDisplay<T>(pub T);

impl<T: DisplayAs> fmt::Display for DefaultDisplay<T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt_as(DisplayFormatType::Default, f)
    }
}

/// A newtype wrapper to display `T` implementing `DisplayAs` using the `Verbose` mode
pub struct VerboseDisplay<T>(pub T);

impl<T: DisplayAs> fmt::Display for VerboseDisplay<T> {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt_as(DisplayFormatType::Verbose, f)
    }
}

/// A wrapper to customize partitioned file display
#[derive(Debug)]
pub struct ProjectSchemaDisplay<'a>(pub &'a SchemaRef);

impl<'a> fmt::Display for ProjectSchemaDisplay<'a> {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let parts: Vec<_> = self
            .0
            .fields()
            .iter()
            .map(|x| x.name().to_owned())
            .collect::<Vec<String>>();
        write!(f, "[{}]", parts.join(", "))
    }
}

/// A wrapper to customize output ordering display.
#[derive(Debug)]
pub struct OutputOrderingDisplay<'a>(pub &'a [PhysicalSortExpr]);

impl<'a> fmt::Display for OutputOrderingDisplay<'a> {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(f, "[")?;
        for (i, e) in self.0.iter().enumerate() {
            if i > 0 {
                write!(f, ", ")?
            }
            write!(f, "{e}")?;
        }
        write!(f, "]")
    }
}

#[cfg(test)]
mod tests {
    use std::fmt::Write;
    use std::sync::Arc;

    use datafusion::common::DataFusionError;

    use datafusion::common::arrow::datatypes::{Schema, SchemaRef};
    use datafusion::physical_plan::{DisplayAs, DisplayFormatType, ExecutionPlan};

    use super::ExtDisplayableExecutionPlan;

    #[derive(Debug, Clone, Copy)]
    enum TestStatsExecPlan {
        Panic,
        Error,
        Ok,
    }

    impl DisplayAs for TestStatsExecPlan {
        fn fmt_as(&self, _t: DisplayFormatType, f: &mut std::fmt::Formatter) -> std::fmt::Result {
            write!(f, "TestStatsExecPlan")
        }
    }

    impl ExecutionPlan for TestStatsExecPlan {
        fn as_any(&self) -> &dyn std::any::Any {
            self
        }

        fn schema(&self) -> SchemaRef {
            Arc::new(Schema::empty())
        }

        fn output_partitioning(&self) -> datafusion::physical_expr::Partitioning {
            datafusion::physical_expr::Partitioning::UnknownPartitioning(1)
        }

        fn output_ordering(&self) -> Option<&[datafusion::physical_expr::PhysicalSortExpr]> {
            None
        }

        fn children(&self) -> Vec<Arc<dyn ExecutionPlan>> {
            vec![]
        }

        fn with_new_children(
            self: Arc<Self>,
            _: Vec<Arc<dyn ExecutionPlan>>,
        ) -> datafusion::common::Result<Arc<dyn ExecutionPlan>> {
            unimplemented!()
        }

        fn execute(
            &self,
            _: usize,
            _: Arc<datafusion::execution::TaskContext>,
        ) -> datafusion::common::Result<datafusion::execution::SendableRecordBatchStream> {
            todo!()
        }

        fn statistics(&self) -> datafusion::common::Result<datafusion::common::Statistics> {
            match self {
                Self::Panic => panic!("expected panic"),
                Self::Error => Err(DataFusionError::Internal("expected error".to_string())),
                Self::Ok => Ok(datafusion::common::Statistics::new_unknown(
                    self.schema().as_ref(),
                )),
            }
        }
    }

    fn test_stats_display(exec: TestStatsExecPlan, show_stats: bool) {
        let display = ExtDisplayableExecutionPlan::new(&exec).set_show_statistics(show_stats);

        let mut buf = String::new();
        write!(&mut buf, "{}", display.one_line()).unwrap();
        let buf = buf.trim();
        assert_eq!(buf, "TestStatsExecPlan");
    }

    #[test]
    fn test_display_when_stats_panic_with_no_show_stats() {
        test_stats_display(TestStatsExecPlan::Panic, false);
    }

    #[test]
    fn test_display_when_stats_error_with_no_show_stats() {
        test_stats_display(TestStatsExecPlan::Error, false);
    }

    #[test]
    fn test_display_when_stats_ok_with_no_show_stats() {
        test_stats_display(TestStatsExecPlan::Ok, false);
    }

    #[test]
    #[should_panic(expected = "expected panic")]
    fn test_display_when_stats_panic_with_show_stats() {
        test_stats_display(TestStatsExecPlan::Panic, true);
    }

    #[test]
    #[should_panic(expected = "Error")] // fmt::Error
    fn test_display_when_stats_error_with_show_stats() {
        test_stats_display(TestStatsExecPlan::Error, true);
    }

    #[test]
    fn test_display_when_stats_ok_with_show_stats() {
        test_stats_display(TestStatsExecPlan::Ok, false);
    }
}
