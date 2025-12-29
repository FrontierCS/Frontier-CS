#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <map>

using namespace std;

int N;
int query_count = 0;

int query(const vector<int>& v) {
    if (v.empty()) return 0;
    cout << "? " << v.size();
    for (int x : v) cout << " " << x;
    cout << endl;
    query_count++;
    int res;
    cin >> res;
    return res;
}

int query2(int u, int v) {
    // Queries pair u, v. Returns 1 if related, 2 if not.
    cout << "? 2 " << u << " " << v << endl;
    query_count++;
    int res;
    cin >> res;
    return res;
}

struct Node {
    int id;
    int signature;
    vector<Node*> children;
    Node(int i) : id(i), signature(0) {}
};

int par[3005];

int main() {
    int ty;
    if (!(cin >> N >> ty)) return 0;

    if (N == 1) {
        cout << "! 0" << endl;
        return 0;
    }

    // 1. Find Root candidates using stack-like elimination
    vector<int> candidates;
    candidates.push_back(1);
    for (int i = 2; i <= N; ++i) {
        if (candidates.empty()) {
            candidates.push_back(i);
            continue;
        }
        int u = candidates.back();
        int res = query2(u, i);
        if (res == 2) {
            // Neither is root. Discard both from consideration for root.
            // u is discarded. i is discarded.
            candidates.pop_back();
            // If candidates is empty after pop, next iteration will push next i
        } else {
            // One is ancestor of other. Keep both (i might be root, or u might be root).
            candidates.push_back(i);
        }
    }

    // The root is in 'candidates' and is the ancestor of all others in 'candidates'.
    // The root is related to ALL nodes.
    // We need to identify the root among candidates.
    // We can use signatures to find the one with max weight (ancestor has superset signature).
    
    // 2. Compute Signatures
    // We use a budget of pivots.
    // Total budget 45000. Reserve some for construction.
    // Use K pivots.
    // Signatures help sorting and filtering children.
    int K = 12; // 12 * 3000 = 36000 queries.
    // If N is small, K can be larger, but 12 is sufficient for sorting.
    
    vector<int> pivots;
    // Select K random pivots from 1..N
    vector<int> p_candidates(N);
    iota(p_candidates.begin(), p_candidates.end(), 1);
    mt19937 rng(1337);
    shuffle(p_candidates.begin(), p_candidates.end(), rng);
    
    for (int i = 0; i < N && pivots.size() < K; ++i) {
        pivots.push_back(p_candidates[i]);
    }

    vector<int> sig(N + 1, 0);
    for (int j = 0; j < pivots.size(); ++j) {
        int p = pivots[j];
        for (int i = 1; i <= N; ++i) {
            if (i == p) {
                sig[i] |= (1 << j);
            } else {
                int res = query2(p, i);
                if (res == 1) {
                    sig[i] |= (1 << j);
                }
            }
        }
    }

    // Identify Root from candidates: Root must have max signature (all 1s basically, if pivots cover enough)
    // Actually Root is related to ALL pivots. So sig[root] must be (1<<K)-1.
    int root = -1;
    for (int u : candidates) {
        if (sig[u] == (1 << pivots.size()) - 1) {
            root = u;
            break;
        }
    }
    // Fallback if pivots didn't cover everything or randomness failed (unlikely)
    if (root == -1) root = candidates[0]; // Should not happen

    // 3. Build Tree
    vector<Node*> nodes(N + 1);
    for (int i = 1; i <= N; ++i) {
        nodes[i] = new Node(i);
        nodes[i]->signature = sig[i];
    }

    Node* tree_root = nodes[root];
    par[root] = 0;

    // Shuffle insertion order to balance the tree construction (randomized BST idea)
    vector<int> insertion_order;
    for (int i = 1; i <= N; ++i) {
        if (i != root) insertion_order.push_back(i);
    }
    shuffle(insertion_order.begin(), insertion_order.end(), rng);

    for (int u_idx : insertion_order) {
        Node* u = nodes[u_idx];
        Node* curr = tree_root;
        
        while (true) {
            // Find children of curr related to u
            // Filter by signature first
            vector<Node*> related_children;
            vector<Node*> potential_children;

            for (Node* c : curr->children) {
                // Check signature compatibility:
                // u related to c => sig(u) subset sig(c) OR sig(c) subset sig(u)
                if ((u->signature & c->signature) == u->signature || 
                    (u->signature & c->signature) == c->signature) {
                    potential_children.push_back(c);
                }
            }
            
            // Check actual relation for filtered children
            for (Node* c : potential_children) {
                if (query2(c->id, u->id) == 1) {
                    related_children.push_back(c);
                }
            }

            if (related_children.empty()) {
                // u is a new child of curr
                curr->children.push_back(u);
                par[u->id] = curr->id;
                break;
            } else if (related_children.size() > 1) {
                // u is parent of all these children
                // u becomes child of curr
                for (Node* c : related_children) {
                    // Remove c from curr->children (will rebuild curr->children list later or simple swap)
                    // Efficient removal:
                    // We can just rebuild curr->children list
                    // Add c to u->children
                    u->children.push_back(c);
                    par[c->id] = u->id;
                }
                
                // Remove related_children from curr->children
                vector<Node*> new_children;
                for (Node* c : curr->children) {
                    bool moved = false;
                    for (Node* rc : related_children) if (rc == c) moved = true;
                    if (!moved) new_children.push_back(c);
                }
                curr->children = new_children;
                curr->children.push_back(u);
                par[u->id] = curr->id;
                break;
            } else {
                // Exactly 1 related child c
                Node* c = related_children[0];
                // Determine direction: is u parent of c or child of c?
                // Use signature inclusion
                // If sig(c) strictly subset sig(u) -> u is parent
                // If sig(u) strictly subset sig(c) -> u is child
                // If equal, assume child (safer to push down)
                
                bool u_is_parent = false;
                if ((c->signature & u->signature) == c->signature && c->signature != u->signature) {
                    u_is_parent = true;
                } else if ((u->signature & c->signature) == u->signature && u->signature != c->signature) {
                    u_is_parent = false;
                } else {
                    // Equal signatures or incomparable (shouldn't happen for related). 
                    // Assume child to recurse.
                    u_is_parent = false; 
                }

                if (u_is_parent) {
                    // u is parent of c
                    // Remove c from curr, add c to u, add u to curr
                     vector<Node*> new_children;
                    for (Node* child : curr->children) {
                        if (child == c) {
                             // Skip c
                        } else {
                            new_children.push_back(child);
                        }
                    }
                    curr->children = new_children;
                    curr->children.push_back(u);
                    par[u->id] = curr->id;
                    
                    u->children.push_back(c);
                    par[c->id] = u->id;
                    break;
                } else {
                    // u is child of c, recurse
                    curr = c;
                }
            }
        }
    }

    cout << "!";
    for (int i = 1; i <= N; ++i) {
        cout << " " << par[i];
    }
    cout << endl;

    return 0;
}