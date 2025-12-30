#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<vector<int>> g, rg;
vector<int> seen;
int timer_cnt = 1;

vector<int> buildPathFrom(int start, bool forwardFirst) {
    ++timer_cnt;
    deque<int> dq;
    dq.push_back(start);
    seen[start] = timer_cnt;

    if (forwardFirst) {
        // Extend forward (outgoing edges from tail) first
        int tail = dq.back();
        while (true) {
            int next = -1;
            const auto &vec = g[tail];
            for (int to : vec) {
                if (seen[to] != timer_cnt) {
                    next = to;
                    break;
                }
            }
            if (next == -1) break;
            dq.push_back(next);
            seen[next] = timer_cnt;
            tail = next;
        }

        // Then extend backward (incoming edges to head)
        int head = dq.front();
        while (true) {
            int next = -1;
            const auto &vec = rg[head];
            for (int from : vec) {
                if (seen[from] != timer_cnt) {
                    next = from;
                    break;
                }
            }
            if (next == -1) break;
            dq.push_front(next);
            seen[next] = timer_cnt;
            head = next;
        }
    } else {
        // Extend backward (incoming edges to head) first
        int head = dq.front();
        while (true) {
            int next = -1;
            const auto &vec = rg[head];
            for (int from : vec) {
                if (seen[from] != timer_cnt) {
                    next = from;
                    break;
                }
            }
            if (next == -1) break;
            dq.push_front(next);
            seen[next] = timer_cnt;
            head = next;
        }

        // Then extend forward (outgoing edges from tail)
        int tail = dq.back();
        while (true) {
            int next = -1;
            const auto &vec = g[tail];
            for (int to : vec) {
                if (seen[to] != timer_cnt) {
                    next = to;
                    break;
                }
            }
            if (next == -1) break;
            dq.push_back(next);
            seen[next] = timer_cnt;
            tail = next;
        }
    }

    vector<int> path;
    path.reserve(dq.size());
    path.assign(dq.begin(), dq.end());
    return path;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> m)) return 0;
    int tmp;
    for (int i = 0; i < 10; ++i) cin >> tmp; // scoring parameters, unused

    g.assign(n + 1, {});
    rg.assign(n + 1, {});
    vector<int> deg(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v);
        rg[v].push_back(u);
        ++deg[u];
        ++deg[v];
    }

    seen.assign(n + 1, 0);

    // Order vertices by degree (sum of in+out) descending
    vector<int> order(n);
    for (int i = 0; i < n; ++i) order[i] = i + 1;
    sort(order.begin(), order.end(), [&](int x, int y) {
        return deg[x] > deg[y];
    });

    int C = min(30, n); // number of starting vertices to try
    vector<int> bestPath;

    for (int i = 0; i < C; ++i) {
        int s = order[i];
        // Two variants: forward-first and backward-first
        vector<int> p1 = buildPathFrom(s, true);
        if (p1.size() > bestPath.size()) bestPath.swap(p1);
        vector<int> p2 = buildPathFrom(s, false);
        if (p2.size() > bestPath.size()) bestPath.swap(p2);
    }

    // Fallback in unlikely case bestPath is empty
    if (bestPath.empty()) {
        bestPath.push_back(1);
    }

    cout << bestPath.size() << '\n';
    for (size_t i = 0; i < bestPath.size(); ++i) {
        if (i) cout << ' ';
        cout << bestPath[i];
    }
    cout << '\n';

    return 0;
}