use serde::{Deserialize, Serialize};

use super::*;

#[derive(Serialize, Deserialize, Debug)]
pub struct YannakakisNode {
    // pub output: Vec<Field>,
    pub root: MultiSemiJoinNode,
}

impl YannakakisNode {
    // Box because of recursion
    pub fn children(&self) -> Box<dyn Iterator<Item = &Node> + '_> {
        self.root.children()
    }
}

#[derive(Serialize, Deserialize, Debug)]
pub struct MultiSemiJoinNode {
    pub equijoin_keys: Vec<Vec<(usize, usize)>>,
    pub guard: Node,
    pub children: Vec<GroupByNode>,
}

impl MultiSemiJoinNode {
    // Box because of recursion
    fn children(&self) -> Box<dyn Iterator<Item = &Node> + '_> {
        let iter = self
            .children
            .iter()
            .flat_map(|child| child.child.children());
        let iter2 = std::iter::once(&self.guard);
        Box::new(iter2.chain(iter))
    }
}

#[derive(Serialize, Deserialize, Debug)]
pub struct GroupByNode {
    pub group_on: Vec<usize>,
    pub child: MultiSemiJoinNode,
}
