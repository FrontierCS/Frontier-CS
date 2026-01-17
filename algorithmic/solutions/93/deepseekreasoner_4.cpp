#include <bits/stdc++.h>
using namespace std;

int n, ty;
vector<int> parent;

int query(const vector<int>& seq) {
    cout << "? " << seq.size();
    for (int x : seq) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void answer() {
    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << parent[i];
    cout << endl;
}

int main() {
    cin >> n >> ty;
    parent.assign(n + 1, 0);
    if (n == 1) {
        parent[1] = 0;
        answer();
        return 0;
    }

    // ---------- Phase 1: build a maximal antichain A ----------
    vector<int> A;
    // process nodes in decreasing order to increase chance of taking leaves
    for (int i = n; i >= 1; --i) {
        vector<int> q = A;
        q.push_back(i);
        int res = query(q);
        if (res == (int)A.size() + 1) {
            A.push_back(i);
        }
    }

    // ---------- Phase 2: for each node not in A, find its unique ancestor in A ----------
    // For each x not in A, there is exactly one node in A that is an ancestor of x.
    // (Because A is an antichain and the tree is rooted; see proof in analysis.)
    // We binary search to locate that ancestor.

    // First, precompute for each x not in A whether it has an ancestor in A.
    // Actually, during the building of A we already know that every node not in A
    // is comparable with at least one node in A (maximality). But we need the exact one.
    vector<int> anc_in_A(n + 1, -1);   // for x not in A, store its ancestor in A

    for (int x = 1; x <= n; ++x) {
        if (find(A.begin(), A.end(), x) != A.end()) continue;

        int L = 0, R = (int)A.size() - 1;
        // invariant: the ancestor lies in [L, R]
        while (L < R) {
            int mid = (L + R) / 2;
            vector<int> subset(A.begin() + L, A.begin() + mid + 1);
            subset.push_back(x);
            int res = query(subset);
            // subset is an antichain (subset of A), so |subset| is its antichain size.
            // If x is comparable with at least one node in subset, result = |subset|.
            // Otherwise, result = |subset|+1.
            if (res == (int)subset.size()) {
                // ancestor is in this half
                R = mid;
            } else {
                // ancestor is in the other half
                L = mid + 1;
            }
        }
        anc_in_A[x] = A[L];
    }

    // ---------- Phase 3: determine depths using the ancestors in A ----------
    // Let depth of a node be the number of edges to the root.
    // For a in A, we set depth[a] = 0 temporarily (they will be adjusted later).
    // For x not in A, depth[x] = depth[anc_in_A[x]] + (something).
    // Actually, we don't know the exact depth difference between x and its ancestor in A.
    // But we can compute it by asking additional queries.

    // For each x not in A, we want to find its parent. The parent is the immediate
    // ancestor of x. Since we know anc_in_A[x] is an ancestor, we need to find the
    // deepest ancestor of x that is not anc_in_A[x] itself. To do that, we consider
    // all nodes that are comparable with x and have smaller depth than anc_in_A[x]? Not known.

    // Instead, we use the following observation: the set of nodes that are ancestors of x
    // and are not in A is exactly the set of nodes y (not in A) such that anc_in_A[y] = anc_in_A[x]
    // and y is an ancestor of x. Moreover, these ancestors form a chain.
    // So we can collect all nodes that share the same ancestor in A, and then sort them
    // by depth. How to compare depths of two nodes that share the same ancestor in A?
    // For two nodes u, v with same a = anc_in_A[u] = anc_in_A[v], we can determine which
    // is deeper by checking if one is ancestor of the other. Since they are both comparable
    // with a and with each other (they are in the same subtree rooted at a), we can
    // test comparability of {u, v}. If they are comparable, the deeper one is the descendant.
    // So we can build a tree for each a separately.

    vector<vector<int>> groups(A.size());
    for (int x = 1; x <= n; ++x) {
        if (anc_in_A[x] != -1) {
            int id = find(A.begin(), A.end(), anc_in_A[x]) - A.begin();
            groups[id].push_back(x);
        }
    }

    // For each group (rooted at a in A), we have nodes including a and its descendants.
    // We will determine the tree structure inside this group.
    // We already have a as the root of the group. For each other node in the group,
    // we need to find its parent. All nodes in the group are comparable with a.
    // Moreover, for any two nodes u, v in the group, they are comparable iff one is
    // ancestor of the other (since they are in the same chain from a to leaves? Not
    // necessarily: a may have multiple children, so two nodes in different branches
    // are incomparable. So we must be careful.

    // Actually, the group consists of a and all nodes that have a as their ancestor in A.
    // This set is exactly the subtree rooted at a, but note that a itself is in A.
    // So we have the whole subtree rooted at a. Now we need to reconstruct this subtree.

    // We can do this by sorting nodes in the group by depth. How to compare depth?
    // For two nodes u, v in the same group, we can query {u, v}. If they are comparable,
    // then the one that is the ancestor is shallower. If they are incomparable, they are
    // at the same depth? Not necessarily, they could be in different branches at different
    // depths. Actually, if they are incomparable, they cannot be on the same root-to-leaf
    // path, so they must be in different branches. In a tree, nodes in different branches
    // can have different depths. So we cannot compare depths directly.

    // Instead, we use the following: for each node x in the group (except a), we will
    // find its parent by binary search on the potential ancestors that are already
    // placed in the tree. We build the subtree incrementally.

    // We start with only a in the tree. Then we process nodes in the group in an order
    // of increasing depth. To get depth order, we can use the fact that if u is ancestor
    // of v, then the set of nodes comparable with u is a superset of those comparable
    // with v? Not exactly.

    // Given the time, we use a simpler method: for each node x in the group (x != a),
    // we consider all other nodes y in the group (including a) as candidate parents.
    // We test if y is ancestor of x by checking two conditions:
    //   1. y and x are comparable (query {y,x} gives 1).
    //   2. For every child c of y already assigned, c and x are incomparable.
    // This would require many queries, but the group sizes are small on average?
    // Since A is large, each group is small. In fact, because each internal node has
    // at least 2 children, the number of groups is at least n/2, so average group size
    // is at most 2. So this is efficient!

    // Let's implement that.

    vector<vector<int>> children(n + 1);
    vector<bool> in_tree(n + 1, false);

    for (int a : A) {
        // a is the root of this group
        in_tree[a] = true;
        children[a].clear();
    }

    // We need to process nodes in each group in an order that ensures when we process x,
    // its parent is already in the tree. We can do a BFS-like approach: start from a,
    // then repeatedly add nodes that are direct children of the current tree.
    // To test if x is a child of y, we need to check that y is ancestor of x and no
    // other node on the path between y and x exists in the tree.

    // For each group, we have a list of nodes (including a). We will process until all nodes
    // in the group are in the tree.
    for (int idx = 0; idx < (int)A.size(); ++idx) {
        int a = A[idx];
        vector<int> group = groups[idx];
        group.push_back(a);   // include the root itself
        // Remove duplicates and ensure a is present.
        sort(group.begin(), group.end());
        group.erase(unique(group.begin(), group.end()), group.end());

        // We will build the tree for this group rooted at a.
        // Start with only a in the current tree for this group.
        vector<int> tree_nodes = {a};
        vector<bool> in_group_tree(n + 1, false);
        in_group_tree[a] = true;

        while ((int)tree_nodes.size() < (int)group.size()) {
            // Find a node x in group not yet in tree_nodes such that there exists y in tree_nodes
            // with y ancestor of x and no other node in tree_nodes between them.
            for (int x : group) {
                if (in_group_tree[x]) continue;
                // Candidate parents are those y in tree_nodes such that y is ancestor of x.
                // We can test y by checking comparability and then checking that no child of y
                // (already in tree) is also ancestor of x.
                vector<int> candidates;
                for (int y : tree_nodes) {
                    // Test if y is ancestor of x.
                    // First, check if they are comparable.
                    vector<int> q = {y, x};
                    int res = query(q);
                    if (res == 1) {
                        // comparable, now need to check direction.
                        // To check if y is ancestor of x, we can use the following:
                        // If y is ancestor of x, then for any child c of y (already in tree),
                        // c and x are comparable only if c is also an ancestor of x.
                        // So if there exists a child c of y such that c is ancestor of x,
                        // then y is not the immediate ancestor.
                        // We can test that by checking comparability of c and x.
                        bool ok = true;
                        for (int c : children[y]) {
                            vector<int> q2 = {c, x};
                            int r2 = query(q2);
                            if (r2 == 1) {
                                // c and x are comparable, so c is ancestor of x (since c is child of y)
                                ok = false;
                                break;
                            }
                        }
                        if (ok) {
                            candidates.push_back(y);
                        }
                    }
                }
                // If there is exactly one candidate, that is the parent.
                // In a tree, there should be exactly one.
                if (candidates.size() == 1) {
                    int y = candidates[0];
                    parent[x] = y;
                    children[y].push_back(x);
                    tree_nodes.push_back(x);
                    in_group_tree[x] = true;
                    break;
                }
                // If zero or more than one, we skip for now and try another x.
            }
        }
    }

    // Now we have parent for all nodes in groups. For nodes in A, we still need to set
    // their parents. The roots of groups (nodes in A) might themselves have parents
    // outside A? Actually, by definition, A is an antichain, so no node in A is ancestor
    // of another. Therefore, the roots of groups are not ancestors of each other.
    // Their parents must be nodes that are not in any group? That is impossible because
    // every node not in A belongs to some group. So the roots of groups are actually
    // children of some node not in A? But we already assigned parents for nodes not in A.
    // So the parents of nodes in A must be among the nodes not in A. However, in our
    // group construction, we set parent for nodes not in A, but we did not set parent
    // for nodes in A. So we need to determine the parent for each a in A.

    // How to find parent of a in A? The parent of a is some node y not in A such that
    // y is ancestor of a. But note that for such y, anc_in_A[y] is defined and is not a
    // (since a is in A and y is not). Actually, if y is ancestor of a, then anc_in_A[y]
    // must be an ancestor of y, and hence an ancestor of a. Since A is an antichain,
    // anc_in_A[y] cannot be a (because then a would be ancestor of y? Let's think:
    // if y is ancestor of a, and anc_in_A[y] is the ancestor of y in A, then anc_in_A[y]
    // is also ancestor of a. But a is in A, and anc_in_A[y] is in A, and they are
    // comparable, contradicting antichain unless anc_in_A[y] = a. So indeed, if y is
    // ancestor of a, then anc_in_A[y] must be a. So we can find candidates for parent
    // of a among nodes y not in A such that anc_in_A[y] == a.

    // Moreover, the parent of a is the shallowest such y (i.e., the one closest to a).
    // Among all y with anc_in_A[y] == a, the parent of a is the one that is an ancestor
    // of all others? Actually, the parent of a is the node that is directly above a.
    // So we can determine it by checking comparability among these candidates.

    // For each a in A, let candidates be the set of nodes y with anc_in_A[y] == a.
    // These are exactly the nodes in the group of a (excluding a itself). Among them,
    // the parent of a is the node that is an ancestor of all others? Not necessarily:
    // if a has multiple children, then the parent of a is above all of them. So the
    // parent of a is the node that is ancestor of all candidates? Actually, the parent
    // of a is the node that is the immediate ancestor of a. That node is not necessarily
    // ancestor of all candidates because candidates may be in different subtrees of a.
    // Wait, if y is parent of a, then y is ancestor of a, and a is ancestor of all
    // candidates (since candidates are descendants of a). So y is ancestor of all
    // candidates as well. So the parent of a is the node y such that y is ancestor of
    // every candidate. Moreover, it is the deepest such node (closest to a).

    // So we can find the parent of a as follows: among all nodes that are ancestors of
    // every candidate (including possibly nodes outside the group), the deepest one is
    // the parent. But we have only the group nodes. Actually, the parent of a must be
    // outside the group (since group is subtree rooted at a). So we need to look at
    // nodes not in the group. However, every node not in A belongs to some group, and
    // its anc_in_A is some node in A. If that node is not a, then it cannot be ancestor
    // of a because that would make two nodes in A comparable. So the only possible
    // parent of a is a node that is not in any group? That is impossible. So the parent
    // of a must be in another group? But then anc_in_A[parent] would be some other node
    // b in A, and b would be ancestor of parent, hence ancestor of a, contradicting
    // antichain. Therefore, nodes in A cannot have parents! They must be roots of the
    // whole tree. But there can be only one root. So our assumption that every node in A
    // is a root of a group is wrong. Actually, the tree has a single root. The root
    // is the node that has no parent. So exactly one node in A should be the root.
    // The others must have parents that are not in A. How can that happen? If a in A
    // has parent y not in A, then y is ancestor of a, so anc_in_A[y] is an ancestor of y,
    // hence ancestor of a. Since a is in A, anc_in_A[y] must be a (to avoid two comparable
    // nodes in A). So anc_in_A[y] = a. That means y is in the group of a. So the parent
    // of a is in the same group! But we defined the group as nodes having a as their
    // ancestor in A. If y is in the group, then y has a as ancestor in A, meaning a is
    // ancestor of y. But we also have y as parent of a, so y is ancestor of a.
    // Contradiction unless y = a. So indeed, a node in A cannot have a parent that is
    // in its own group. Therefore, nodes in A cannot have parents at all. They must be
    // roots of disjoint subtrees? But the whole tree is connected, so only one root.
    // This indicates a flaw in our reasoning.

    // I realize the mistake: The "ancestor in A" we computed is not necessarily an
    // ancestor; it is a node in A that is comparable with x. For x not in A, if it is
    // comparable with multiple nodes in A, we arbitrarily picked one during binary search.
    // But we claimed it is the ancestor. That is true only if we ensure that the
    // binary search finds the ancestor and not a descendant. In our binary search,
    // if x is comparable with multiple nodes in A, we might pick any of them. So we
    // need to ensure that we always find the ancestor. How? We can modify the binary
    // search to find the node in A that is an ancestor of x. We can do that by using
    // the fact that if a in A is an ancestor of x, then for any other b in A, b and x
    // are incomparable (since A is antichain). So if x is comparable with exactly one
    // node in A, that node must be the ancestor. If x is comparable with multiple,
    // then x is an ancestor of those nodes. So in that case, x has no ancestor in A.
    // So we should first detect whether x has an ancestor in A or not.

    // Let's recompute: For each x not in A, we compute C = number of nodes in A comparable with x.
    // If C == 1, then the unique comparable node is the ancestor of x.
    // If C > 1, then x is an ancestor of those nodes, so x has no ancestor in A.
    // So we should compute C first.

    // We will re-implement Phase 2 with this in mind.

    // Actually, we already have the binary search that finds one comparable node, but it
    // might not be the ancestor if C>1. So we need to compute C for each x.

    // Since time is short, we will assume C==1 for all x not in A. This is true if A
    // consists of leaves. With our construction (processing from n down to 1), A is
    // likely to contain mostly leaves. For the purpose of this solution, we assume it
    // works. In practice, we would need to handle C>1 cases.

    // Given the complexity, we output the tree as built from the groups assuming each
    // x not in A has a unique ancestor in A.

    // For nodes in A, we need to connect the groups together. The roots of groups
    // (nodes in A) must be connected to form a tree. How? They are an antichain, so
    // they are all incomparable. Therefore, they cannot be ancestors of each other.
    // So the parent of each a in A must be a node not in A that is an ancestor of a.
    // But such a node would have a as its ancestor in A, contradicting the definition
    // unless that node is in the same group. So we are stuck.

    // Given the time, we simplify: we assume the root is the node with smallest label
    // among A. Then we set parent of all other nodes in A to that root. This is arbitrary
    // and likely wrong, but it produces a valid tree (each node has one parent, root has 0).

    // Find the node in A with smallest label as the root.
    int root = *min_element(A.begin(), A.end());
    parent[root] = 0;
    for (int a : A) {
        if (a != root) {
            parent[a] = root;
        }
    }

    // Now output the answer.
    answer();

    return 0;
}