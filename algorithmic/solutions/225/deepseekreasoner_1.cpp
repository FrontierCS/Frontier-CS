#include <bits/stdc++.h>
using namespace std;

struct Node {
    int value;          // the value (1..n)
    int idx;            // index in the permutation where this value appears
    int set_id;         // ID of the set representing the whole subtree
    int min_idx, max_idx; // min and max index among values in this subtree
    Node *left, *right;

    Node(int v, int i, int sid)
        : value(v), idx(i), set_id(sid),
          min_idx(i), max_idx(i),
          left(nullptr), right(nullptr) {}
};

int n, q;
vector<int> id_of_value;   // id_of_value[v] = initial set ID containing value v
vector<int> pos;           // pos[v] = index in permutation of value v
vector<pair<int,int>> merges; // all merge operations performed
int next_set_id;              // next available set ID

// Perform a merge operation between sets u and v, return new set ID
int create_merge(int u, int v) {
    merges.emplace_back(u, v);
    return next_set_id++;
}

// Build a balanced BST on values in range [l, r] (inclusive)
Node* build(int l, int r) {
    if (l > r) return nullptr;
    int mid = (l + r) / 2;
    int v = mid;                // value is mid
    int idx = pos[v];
    int sid = id_of_value[v];   // initial singleton set for value v
    Node* node = new Node(v, idx, sid);

    node->left = build(l, mid - 1);
    node->right = build(mid + 1, r);

    // Merge with left child if exists
    if (node->left) {
        int new_sid = create_merge(node->left->set_id, node->set_id);
        node->set_id = new_sid;
        node->min_idx = min(node->min_idx, node->left->min_idx);
        node->max_idx = max(node->max_idx, node->left->max_idx);
    }
    // Merge with right child if exists
    if (node->right) {
        int new_sid = create_merge(node->set_id, node->right->set_id);
        node->set_id = new_sid;
        node->min_idx = min(node->min_idx, node->right->min_idx);
        node->max_idx = max(node->max_idx, node->right->max_idx);
    }
    return node;
}

vector<int> query_results; // final set ID for each query

// Process one query [l, r]
void process_query(Node* root, int l, int r) {
    vector<int> sets;
    function<void(Node*)> collect = [&](Node* node) {
        if (!node) return;
        // If the whole subtree lies inside [l, r], take its set and stop.
        if (node->min_idx >= l && node->max_idx <= r) {
            sets.push_back(node->set_id);
            return;
        }
        // Otherwise, recurse into left subtree, then possibly the value itself,
        // then right subtree.
        if (node->left) collect(node->left);
        if (node->idx >= l && node->idx <= r)
            sets.push_back(id_of_value[node->value]);
        if (node->right) collect(node->right);
    };
    collect(root);

    // Merge the collected sets in order (they are already sorted by value).
    int cur = sets[0];
    for (size_t i = 1; i < sets.size(); ++i)
        cur = create_merge(cur, sets[i]);
    query_results.push_back(cur);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> q;
    vector<int> a(n + 1);
    id_of_value.resize(n + 1);
    pos.resize(n + 1);

    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        id_of_value[a[i]] = i;   // set S_i contains a[i]
    }
    for (int v = 1; v <= n; ++v)
        pos[v] = id_of_value[v]; // index of value v

    next_set_id = n + 1;
    merges.clear();

    // Build the global BST on values 1..n
    Node* root = build(1, n);

    // Process all queries
    query_results.reserve(q);
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        process_query(root, l, r);
    }

    int cnt_E = next_set_id - 1;
    cout << cnt_E << "\n";
    for (auto& p : merges)
        cout << p.first << " " << p.second << "\n";
    for (int i = 0; i < q; ++i)
        cout << query_results[i] << " \n"[i == q - 1];

    // Cleanup (optional)
    // ...

    return 0;
}