#include <bits/stdc++.h>
using namespace std;

const int MAXN = 5000; // n <= 4096

int n, q;
int a[MAXN+5];
int inv[MAXN+5]; // inv[x] = index i such that a[i] = x

int cnt; // current number of sets, initially n

struct Node {
    int L, R;          // value range [L,R]
    int set_id;        // ID of the set containing exactly {L,...,R}
    int min_idx, max_idx; // min and max of inv over [L,R]
} tree[4 * MAXN];

vector<pair<int, int>> merges; // all merge operations in order
vector<int> answers; // answer set ID for each query

void build(int node, int l, int r) {
    tree[node].L = l;
    tree[node].R = r;
    if (l == r) {
        tree[node].set_id = inv[l]; // initial set containing {l}
        tree[node].min_idx = inv[l];
        tree[node].max_idx = inv[l];
        return;
    }
    int mid = (l + r) / 2;
    int left = node * 2, right = node * 2 + 1;
    build(left, l, mid);
    build(right, mid+1, r);
    
    tree[node].min_idx = min(tree[left].min_idx, tree[right].min_idx);
    tree[node].max_idx = max(tree[left].max_idx, tree[right].max_idx);
    
    // merge left and right sets
    int u = tree[left].set_id;
    int v = tree[right].set_id;
    int new_id = ++cnt;
    merges.push_back({u, v});
    tree[node].set_id = new_id;
}

void collect(int node, int ql, int qr, vector<int>& vec) {
    // if the whole node's indices are inside [ql,qr], take it
    if (tree[node].min_idx >= ql && tree[node].max_idx <= qr) {
        vec.push_back(tree[node].set_id);
        return;
    }
    if (tree[node].L == tree[node].R) {
        // leaf not fully contained -> skip
        return;
    }
    collect(node * 2, ql, qr, vec);
    collect(node * 2 + 1, ql, qr, vec);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    cin >> n >> q;
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        inv[a[i]] = i;
    }
    
    cnt = n; // initial sets S1..Sn
    build(1, 1, n); // build value segment tree
    
    // process queries
    for (int i = 0; i < q; i++) {
        int l, r;
        cin >> l >> r;
        vector<int> sets;
        collect(1, l, r, sets); // collect maximal fully contained nodes
        
        // merge the collected sets in order
        if (sets.empty()) {
            // should not happen because l <= r
            // but to be safe, we can create an empty set? Not needed.
        }
        int cur_id = sets[0];
        for (size_t j = 1; j < sets.size(); j++) {
            int new_id = ++cnt;
            merges.push_back({cur_id, sets[j]});
            cur_id = new_id;
        }
        answers.push_back(cur_id);
    }
    
    // output
    cout << cnt << "\n";
    for (auto& op : merges) {
        cout << op.first << " " << op.second << "\n";
    }
    for (int i = 0; i < q; i++) {
        cout << answers[i] << (i+1 == q ? "\n" : " ");
    }
    
    return 0;
}