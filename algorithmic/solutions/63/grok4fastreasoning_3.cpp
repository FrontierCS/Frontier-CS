#include <bits/stdc++.h>
using namespace std;

const int MAXN = 10005;
int vis[MAXN];
int timestamp_ = 0;
int N, M;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    cout.tie(NULL);
    srand(time(NULL));

    cin >> N >> M;
    vector<pair<int, int>> edges(M);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        if (u > v) swap(u, v);
        edges[i] = {u, v};
    }

    vector<bitset<MAXN>> possibleB(N);
    for (int i = 0; i < N; i++) {
        possibleB[i].set();
        if (i < N) possibleB[i][i] = 0;
    }

    memset(vis, 0, sizeof(vis));
    timestamp_ = 0;

    int qcount = 0;
    while (true) {
        qcount++;
        // compute total_pairs
        long long total_pairs = 0;
        for (int i = 0; i < N; i++) {
            total_pairs += possibleB[i].count();
        }
        if (total_pairs == 1) {
            // find the pair
            for (int a = 0; a < N; a++) {
                if (possibleB[a].count() == 1) {
                    for (int b = 0; b < N; b++) {
                        if (possibleB[a][b]) {
                            cout << 1 << " " << a << " " << b << endl;
                            cout.flush();
                            return 0;
                        }
                    }
                }
            }
        }
        if (qcount > 600) {
            // should not happen
            assert(false);
        }

        // make query
        vector<int> choice(M);
        for (int i = 0; i < M; i++) {
            choice[i] = rand() % 2;
        }

        // output
        cout << 0;
        for (int d : choice) {
            cout << " " << d;
        }
        cout << endl;
        cout.flush();

        int x;
        cin >> x;

        // build dir_adj
        vector<vector<int>> dir_adj(N);
        for (int e = 0; e < M; e++) {
            int u = edges[e].first;
            int v = edges[e].second;
            if (choice[e] == 0) {
                dir_adj[u].push_back(v);
            } else {
                dir_adj[v].push_back(u);
            }
        }

        // update
        timestamp_++;
        if (timestamp_ == 0) {
            timestamp_ = 1;
            memset(vis, 0, sizeof(vis));
        }
        for (int a = 0; a < N; a++) {
            if (possibleB[a].none()) continue;
            // BFS from a
            bitset<MAXN> reach;
            reach.reset();
            queue<int> qq;
            if (vis[a] != timestamp_) {
                vis[a] = timestamp_;
                qq.push(a);
                reach[a] = 1;
            }
            while (!qq.empty()) {
                int u = qq.front();
                qq.pop();
                for (int v : dir_adj[u]) {
                    if (vis[v] != timestamp_) {
                        vis[v] = timestamp_;
                        reach[v] = 1;
                        qq.push(v);
                    }
                }
            }
            // update possibleB[a]
            if (x == 1) {
                possibleB[a] &= reach;
            } else {
                possibleB[a] &= ~reach;
            }
            possibleB[a][a] = 0;
        }
    }
    return 0;
}