#include <bits/stdc++.h>
using namespace std;

const int MAXN = 4096; // 2^12
const int MAXQ = 65536; // 2^16

int n, q;
int a[MAXN + 1];
int pos[MAXN + 1];        // pos[value] = index
int cnt;                  // current number of sets, initially n
vector<pair<int, int>> ops; // merge operations
vector<int> ans_k;        // answer set ids for queries

// segment tree on values [1..n]
int minpos[4 * MAXN];
int maxpos[4 * MAXN];
int node_id[4 * MAXN];    // set id for this node

void build(int node, int l, int r) {
    if (l == r) {
        minpos[node] = maxpos[node] = pos[l];
        node_id[node] = pos[l]; // singleton set id = index of value l
        return;
    }
    int mid = (l + r) / 2;
    build(node * 2, l, mid);
    build(node * 2 + 1, mid + 1, r);
    minpos[node] = min(minpos[node * 2], minpos[node * 2 + 1]);
    maxpos[node] = max(maxpos[node * 2], maxpos[node * 2 + 1]);
    // merge left and right children (left values are all smaller)
    int u = node_id[node * 2];
    int v = node_id[node * 2 + 1];
    ops.push_back({u, v});
    cnt++;
    node_id[node] = cnt;
}

void query_collect(int node, int l, int r, int ql, int qr, vector<int>& collected) {
    if (maxpos[node] < ql || minpos[node] > qr) return;
    if (minpos[node] >= ql && maxpos[node] <= qr) {
        collected.push_back(node_id[node]);
        return;
    }
    if (l == r) return; // leaf not fully contained
    int mid = (l + r) / 2;
    query_collect(node * 2, l, mid, ql, qr, collected);
    query_collect(node * 2 + 1, mid + 1, r, ql, qr, collected);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n >> q;
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        pos[a[i]] = i;
    }
    cnt = n;
    build(1, 1, n);
    ans_k.resize(q);
    for (int i = 0; i < q; i++) {
        int l, r;
        cin >> l >> r;
        vector<int> collected;
        query_collect(1, 1, n, l, r, collected);
        int cur = collected[0];
        for (size_t j = 1; j < collected.size(); j++) {
            int next = collected[j];
            ops.push_back({cur, next});
            cnt++;
            cur = cnt;
        }
        ans_k[i] = cur;
    }
    // output
    cout << cnt << '\n';
    for (auto& p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }
    for (int i = 0; i < q; i++) {
        cout << ans_k[i] << " \n"[i == q - 1];
    }
    return 0;
}