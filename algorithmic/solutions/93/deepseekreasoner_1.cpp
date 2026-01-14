#include <bits/stdc++.h>
using namespace std;

int n, ty;
map<pair<int, int>, int> memo;

int ask(const vector<int>& seq) {
    cout << "? " << seq.size();
    for (int x : seq) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

int compare(int a, int b) {
    if (a == b) return 1;
    if (a > b) swap(a, b);
    if (memo.count({a, b})) return memo[{a, b}];
    vector<int> seq = {a, b};
    int res = ask(seq);
    memo[{a, b}] = res;
    return res;
}

int main() {
    cin >> n >> ty;
    vector<int> f(n + 1);
    // compute f[i]: result of query [i, then all others in increasing order]
    for (int i = 1; i <= n; ++i) {
        vector<int> seq = {i};
        for (int j = 1; j <= n; ++j)
            if (j != i) seq.push_back(j);
        f[i] = ask(seq);
    }
    // order nodes by f ascending (root first)
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return f[a] < f[b];
    });
    vector<int> parent(n + 1, 0);
    // for each node, find its parent among earlier nodes in order
    for (int idx = 1; idx < n; ++idx) {
        int x = order[idx];
        // scan backwards for a candidate ancestor
        for (int j = idx - 1; j >= 0; --j) {
            int y = order[j];
            if (compare(y, x) == 1) { // comparable
                // assume y is ancestor (since f[y] < f[x])
                parent[x] = y;
                break;
            }
        }
    }
    // root has parent 0
    parent[order[0]] = 0;
    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << parent[i];
    cout << endl;
    cout.flush();
    return 0;
}