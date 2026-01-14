#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <functional>

using namespace std;

struct Op {
    int type;
    int pos;
};

// Represents a node in the parenthesis tree
struct Node {
    int id; // For debugging or tracking
    vector<Node*> children;
    // The substring range in current string is not stored explicitly, 
    // but structure is maintained.
};

// Global to count operations
int n;
string current_s;
vector<Op> ops;

// Helper to apply operation on string for verification (optional/debugging)
// and to track positions.
// Since operations change lengths/indices, we need to be careful.
// But the problem asks for indices in the current string.
// We will simulate the process on a tree structure and generate ops.
// Wait, the positions are linear indices.
// Maintaining the tree and mapping to linear indices is crucial.

// Tree Node
struct TreeNode {
    vector<TreeNode*> children;
    int size; // total size in characters (2 * total pairs)
    
    TreeNode() : size(2) {} // minimal size () is 2
    
    void update_size() {
        size = 2;
        for (auto c : children) size += c->size;
    }
};

TreeNode* parse(const string& s, int& pos) {
    TreeNode* node = new TreeNode();
    pos++; // consume '('
    while (pos < s.length() && s[pos] == '(') {
        node->children.push_back(parse(s, pos));
    }
    pos++; // consume ')'
    node->update_size();
    return node;
}

// Global root for current tree
TreeNode* root;

// Function to calculate position of a child
int get_child_pos(TreeNode* parent, int child_idx, int parent_pos) {
    int current_pos = parent_pos + 1; // skip parent's '('
    for (int i = 0; i < child_idx; ++i) {
        current_pos += parent->children[i]->size;
    }
    return current_pos;
}

// Operation functions that manipulate the tree and record op
void op1(TreeNode* parent, int child_idx, int abs_pos, vector<Op>& op_list) {
    // (((A)B)C) -> ((A)B)(C)
    // parent has child at child_idx.
    // child matches structure ( ((A)B) C ).
    // child has a child0 which is ((A)B).
    // child0 has child0 which is (A). child0 also has B as remaining children.
    // Actually, tree structure:
    // child is the node corresponding to outer parens of LHS.
    // Inside child: first child is `node_AB` (wrapper of A, B).
    // Remaining children of child are C.
    // Operation: 
    // `child` is replaced by `node_AB` and `new_node_C`.
    // Wait, the operation happens at `parent` level?
    // Op 1 description: p (((A)B)C) q -> p ((A)B)(C) q
    // The target is the block (((A)B)C).
    // It is split into ((A)B) and (C).
    // So `parent` children list changes. `child` is removed, replaced by `node_AB` and `node_C`.
    
    TreeNode* node = parent->children[child_idx];
    TreeNode* node_AB = node->children[0];
    
    // Construct node_C
    TreeNode* node_C = new TreeNode();
    node_C->children.insert(node_C->children.end(), node->children.begin() + 1, node->children.end());
    node_C->update_size();
    
    // Update parent list
    // Replace `node` with `node_AB` and `node_C`
    // Wait, RHS is ((A)B)(C).
    // node_AB is ((A)B). node_C is (C).
    
    parent->children[child_idx] = node_AB;
    parent->children.insert(parent->children.begin() + child_idx + 1, node_C);
    
    op_list.push_back({1, abs_pos});
    
    delete node;
    parent->update_size();
}

void op2(TreeNode* parent, int child_idx, int abs_pos, vector<Op>& op_list) {
    // ((A)(B)C) -> ((A)B)(C)
    // Target is block ((A)(B)C).
    // Inside: child0=(A), child1=(B), rest=C.
    // RHS: New block ((A)B) and block (C).
    
    TreeNode* node = parent->children[child_idx];
    TreeNode* A = node->children[0];
    TreeNode* B = node->children[1];
    
    // Construct ((A)B)
    TreeNode* new_node = new TreeNode();
    new_node->children.push_back(A);
    // B's contents become children of new_node after A
    new_node->children.insert(new_node->children.end(), B->children.begin(), B->children.end());
    new_node->update_size();
    
    // Construct (C)
    TreeNode* node_C = new TreeNode();
    node_C->children.insert(node_C->children.end(), node->children.begin() + 2, node->children.end());
    node_C->update_size();
    
    // Replace in parent
    parent->children[child_idx] = new_node;
    parent->children.insert(parent->children.begin() + child_idx + 1, node_C);
    
    op_list.push_back({2, abs_pos});
    
    delete node;
    delete B; // B wrapper is gone
    parent->update_size();
}

void op4(TreeNode* parent, int child_idx, int abs_pos, vector<Op>& op_list) {
    // (A)(B)(C) -> ((A)B)(C)
    // Merge child[child_idx] and child[child_idx+1].
    
    TreeNode* A = parent->children[child_idx];
    TreeNode* B = parent->children[child_idx+1];
    // C is just context, not touched essentially, but pattern requires it.
    // Actually pattern is p (A)(B)(C) q.
    // The operation merges first two.
    
    TreeNode* new_node = new TreeNode();
    new_node->children.push_back(A);
    new_node->children.insert(new_node->children.end(), B->children.begin(), B->children.end());
    new_node->update_size();
    
    parent->children[child_idx] = new_node;
    parent->children.erase(parent->children.begin() + child_idx + 1);
    
    op_list.push_back({4, abs_pos});
    
    delete B; 
    parent->update_size();
}

// Flatten strategy for S1 (can use Op 2)
void flatten_s1(TreeNode* node, int abs_pos, vector<Op>& op_list) {
    // Flatten children first
    int current_child_pos = abs_pos + 1;
    for (int i = 0; i < node->children.size(); ++i) {
        flatten_s1(node->children[i], current_child_pos, op_list);
        current_child_pos += node->children[i]->size;
        node->update_size(); // size might change? No, flattening preserves size
    }
    
    // Now flatten current node
    while (node->children.size() > 1) {
        // Use Op 2 to split: ((A)(B)C) -> ((A)B)(C)
        // Effectively peels off C.
        // We want to reduce children count.
        // Op 2 splits `node` into `node_new` and `node_C`.
        // BUT `node` is not the target of op2 here.
        // We are inside `node`.
        // We need to apply Op 2 on `node`.
        // But Op 2 is applied on a child of parent.
        // So we cannot reduce `node` itself unless we are at parent.
        // This function visits `node`. Operations must be done by parent?
        // Let's change approach: process children from parent.
        break; 
    }
}

// Flatten list of children in parent
void flatten_children_s1(TreeNode* parent, int parent_abs_pos, vector<Op>& op_list) {
    // Recursively flatten each child
    int pos = parent_abs_pos + 1;
    for (int i = 0; i < parent->children.size(); ++i) {
        flatten_children_s1(parent->children[i], pos, op_list);
        pos += parent->children[i]->size;
    }
    parent->update_size();

    // Now reduce this node's children
    // If we have children C1, C2, ...
    // If C1 has form ((A)B), we can use Op 1 to split C1 -> (A), (B).
    // This increases number of children.
    // If we have C1, C2, C3, we can use Op 4 to merge C1, C2 -> ((C1)C2).
    // We want to Flatten S1. Flatten means increasing block count (Splitting).
    
    bool changed = true;
    while (changed) {
        changed = false;
        pos = parent_abs_pos + 1;
        for (int i = 0; i < parent->children.size(); ++i) {
            TreeNode* child = parent->children[i];
            // Try Op 1: child = ( ((A)B) C )
            if (child->children.size() > 0) {
                TreeNode* inner = child->children[0];
                if (inner->children.size() > 0) { // inner starts with ( ... ) -> matches ((A)B)
                    op1(parent, i, pos, op_list);
                    changed = true;
                    break;
                }
            }
            // Try Op 2: child = ( (A)(B)C )
            if (child->children.size() >= 2) {
                op2(parent, i, pos, op_list);
                changed = true;
                break;
            }
            pos += child->size;
        }
    }
}

// Flatten for S2 (ONLY Op 1 allowed for reversibility)
void flatten_children_s2(TreeNode* parent, int parent_abs_pos, vector<Op>& op_list) {
    int pos = parent_abs_pos + 1;
    for (int i = 0; i < parent->children.size(); ++i) {
        flatten_children_s2(parent->children[i], pos, op_list);
        pos += parent->children[i]->size;
    }
    parent->update_size();

    bool changed = true;
    while (changed) {
        changed = false;
        pos = parent_abs_pos + 1;
        for (int i = 0; i < parent->children.size(); ++i) {
            TreeNode* child = parent->children[i];
            // Only Op 1
            if (child->children.size() > 0) {
                TreeNode* inner = child->children[0];
                if (inner->children.size() > 0) {
                    op1(parent, i, pos, op_list);
                    changed = true;
                    break;
                }
            }
            pos += child->size;
        }
    }
}

// Merge to Chain
void merge_to_chain(TreeNode* parent, int parent_abs_pos, vector<Op>& op_list) {
    // Parent has list of children (blocks).
    // We want to merge them into one block.
    // Use Op 4. (A)(B)(C) -> ((A)B)(C).
    // Requires 3 blocks.
    
    while (parent->children.size() > 1) {
        if (parent->children.size() >= 3) {
            // Merge first two
            op4(parent, 0, parent_abs_pos + 1, op_list);
        } else {
            // Size is 2. (A)(B).
            // Cannot use Op 4 directly.
            // But we can recurse on A?
            // Actually, we are building chain.
            // Just one block is enough.
            // If we have 2 blocks, we are stuck?
            // Ops 5/6 allowed max 2 times.
            // Insert () -> 3 blocks.
            // Op 4 -> 2 blocks.
            // Remove ()?
            // We can't rely on this often.
            // But usually we have many blocks.
            // If we reduce to 2 blocks, we stop?
            // If we stop with 2 blocks, it's not a Chain.
            // But s1 and s2 both stop at 2 blocks (canonical form is "near Chain").
            break;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_val;
    if (!(cin >> n_val)) return 0;
    string s1_str, s2_str;
    cin >> s1_str >> s2_str;

    // Fake root to hold top-level sequence
    TreeNode* root1 = new TreeNode(); 
    root1->children.push_back(new TreeNode()); // dummy wrapper
    // Actually, parse will return a list of nodes? 
    // No, parse returns one node.
    // Wrap s1 in parens to make it a single tree
    string s1_wrapped = "(" + s1_str + ")";
    int pos = 0;
    TreeNode* tree1 = parse(s1_wrapped, pos);
    
    string s2_wrapped = "(" + s2_str + ")";
    pos = 0;
    TreeNode* tree2 = parse(s2_wrapped, pos);

    vector<Op> ops1;
    // Flatten S1
    flatten_children_s1(tree1, 0, ops1); 
    // Merge S1 to Chain
    merge_to_chain(tree1, 0, ops1);
    
    vector<Op> ops2;
    // Flatten S2 (restricted)
    flatten_children_s2(tree2, 0, ops2);
    // Merge S2 to Chain
    merge_to_chain(tree2, 0, ops2);

    // Output
    cout << ops1.size() + ops2.size() << "\n";
    for (auto& op : ops1) {
        // Adjust pos because we wrapped s1
        // Wrapped: ( s1 )
        // Op at pos x in wrapped means x relative to outer (.
        // Real pos is x - 1.
        cout << op.type << " " << op.pos - 1 << "\n";
    }
    // Print ops2 reversed
    reverse(ops2.begin(), ops2.end());
    for (auto& op : ops2) {
        int type = op.type;
        int p = op.pos - 1;
        // Reverse types: 4 <-> 1.
        if (type == 4) type = 1;
        else if (type == 1) type = 4;
        cout << type << " " << p << "\n";
    }

    return 0;
}