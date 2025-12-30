#include <iostream>
#include <vector>
#include <algorithm>
#include <cstdlib>
#include <ctime>

using namespace std;

// Fenwick Tree for finding Max Weight Increasing Subsequence
// Stores {sum, length, index}
struct Info {
    long long sum;
    int len;
    int index; // index in the original permutation to reconstruct S
    
    // Comparison for "better" IS: larger sum, then larger length
    bool operator<(const Info& other) const {
        if (sum != other.sum) return sum < other.sum;
        return len < other.len;
    }
};

const int MAXN = 300005;
Info bit[MAXN];
int n;

void update(int idx, Info val) {
    for (; idx <= n; idx += idx & -idx) {
        if (bit[idx] < val) {
            bit[idx] = val;
        }
    }
}

Info query(int idx) {
    Info res = {0, 0, -1};
    for (; idx > 0; idx -= idx & -idx) {
        if (res < bit[idx]) {
            res = bit[idx];
        }
    }
    return res;
}

// Treap Implementation for simulating moves efficiently
struct Node {
    int val;
    int priority;
    int size;
    Node *left, *right, *parent;
    
    Node(int v) : val(v), priority(rand()), size(1), left(nullptr), right(nullptr), parent(nullptr) {}
};

int get_size(Node* t) {
    return t ? t->size : 0;
}

void update_size(Node* t) {
    if (t) {
        t->size = 1 + get_size(t->left) + get_size(t->right);
        if (t->left) t->left->parent = t;
        if (t->right) t->right->parent = t;
    }
}

// Split by implicit index (k elements in left tree)
void split(Node* t, int k, Node*& l, Node*& r) {
    if (!t) {
        l = r = nullptr;
        return;
    }
    int cur_idx = get_size(t->left) + 1;
    if (cur_idx <= k) {
        split(t->right, k - cur_idx, t->right, r);
        l = t;
    } else {
        split(t->left, k, l, t->left);
        r = t;
    }
    update_size(t);
}

void merge(Node*& t, Node* l, Node* r) {
    if (!l || !r) {
        t = l ? l : r;
    } else if (l->priority > r->priority) {
        merge(l->right, l->right, r);
        t = l;
    } else {
        merge(r->left, l, r->left);
        t = r;
    }
    update_size(t);
}

// Get rank of a node (1-based index in the sequence)
int get_rank(Node* t) {
    int r = get_size(t->left) + 1;
    while (t->parent) {
        if (t->parent->right == t) {
            r += get_size(t->parent->left) + 1;
        }
        t = t->parent;
    }
    return r;
}

Node* nodes[MAXN]; // Direct access to nodes by value

void insert_at(Node*& root, int idx, int val) {
    Node* l;
    Node* r;
    split(root, idx - 1, l, r);
    if (l) l->parent = nullptr;
    if (r) r->parent = nullptr;
    
    nodes[val] = new Node(val);
    merge(l, l, nodes[val]);
    merge(root, l, r);
    if (root) root->parent = nullptr; 
}

void remove_val(Node*& root, int val) {
    int rk = get_rank(nodes[val]);
    Node *l, *m, *r;
    split(root, rk, m, r);
    if (m) m->parent = nullptr;
    if (r) r->parent = nullptr;
    
    split(m, rk - 1, l, m);
    if (l) l->parent = nullptr;
    // m is the node to delete (we just drop it)
    
    merge(root, l, r);
    if (root) root->parent = nullptr;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));

    if (!(cin >> n)) return 0;

    vector<int> v(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> v[i];
    }

    // MWIS with BIT
    vector<int> prev_idx(n + 1, -1);
    Info best_global = {0, 0, -1};

    // Initialize BIT
    for(int i=0; i<=n; ++i) bit[i] = {0, 0, -1};

    for (int i = 1; i <= n; ++i) {
        Info best = query(v[i] - 1);
        Info current = {best.sum + v[i], best.len + 1, i};
        prev_idx[i] = best.index;
        update(v[i], current);
        if (best_global < current) {
            best_global = current;
        }
    }

    // Reconstruct S
    vector<bool> is_in_S(n + 1, false);
    int curr = best_global.index;
    while (curr != -1) {
        is_in_S[v[curr]] = true;
        curr = prev_idx[curr];
    }

    vector<int> U;
    for (int i = 1; i <= n; ++i) {
        if (!is_in_S[i]) {
            U.push_back(i);
        }
    }
    // Sort U descending
    sort(U.rbegin(), U.rend());

    long long len_moves = U.size();
    long long sum_U = 0;
    for (int u : U) sum_U += u;
    long long total_cost = sum_U - (len_moves * (len_moves - 1)) / 2;
    
    long long final_score = (total_cost + 1) * (len_moves + 1);
    cout << final_score << " " << len_moves << "\n";

    // Prepare moves using Treap
    Node* root = nullptr;
    for (int i = 1; i <= n; ++i) {
        insert_at(root, i, v[i]);
    }

    for (int i = 0; i < U.size(); ++i) {
        int val = U[i];
        int current_pos = get_rank(nodes[val]);
        int num_smaller = (int)U.size() - 1 - i;
        int target_pos = val - num_smaller;
        
        cout << current_pos << " " << target_pos << "\n";
        
        remove_val(root, val);
        insert_at(root, target_pos, val);
    }

    return 0;
}