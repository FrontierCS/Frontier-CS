#include <bits/stdc++.h>
using namespace std;

using ll = long long;

static inline ll ask(int x, int y) {
    cout << "QUERY " << x << " " << y << endl;
    cout.flush();
    ll v;
    if (!(cin >> v)) exit(0);
    return v;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long k;
    if (!(cin >> n >> k)) return 0;

    long long total = 1LL * n * n;
    if (k < 1) k = 1;
    if (k > total) k = total;

    struct Node {
        long long key;
        int row;
    };
    auto cmp = [](const Node& a, const Node& b) { return a.key > b.key; };
    priority_queue<Node, vector<Node>, decltype(cmp)> pq(cmp);

    long long ans = 0;

    if (k <= total - k + 1) {
        // Ascending: merge rows from left to right
        vector<int> ptr(n + 1, 1);
        for (int i = 1; i <= n; ++i) {
            ll v = ask(i, 1);
            pq.push({v, i});
        }
        for (long long cnt = 1; cnt <= k; ++cnt) {
            Node cur = pq.top(); pq.pop();
            ans = cur.key;
            if (cnt == k) break;
            int i = cur.row;
            int j = ++ptr[i];
            if (j <= n) {
                ll v = ask(i, j);
                pq.push({v, i});
            }
        }
    } else {
        // Descending: merge rows from right to left to get the (total - k + 1)-th largest
        long long t = total - k + 1;
        vector<int> ptr(n + 1, n);
        for (int i = 1; i <= n; ++i) {
            ll v = ask(i, n);
            pq.push({-v, i}); // use negative to simulate max-heap with min-heap
        }
        for (long long cnt = 1; cnt <= t; ++cnt) {
            Node cur = pq.top(); pq.pop();
            ans = -cur.key;
            if (cnt == t) break;
            int i = cur.row;
            int j = --ptr[i];
            if (j >= 1) {
                ll v = ask(i, j);
                pq.push({-v, i});
            }
        }
    }

    cout << "DONE " << ans << endl;
    cout.flush();
    return 0;
}