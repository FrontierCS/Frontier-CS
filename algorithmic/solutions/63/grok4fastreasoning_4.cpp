#include <bits/stdc++.h>
using namespace std;

const int MAXN = 10010;
bitset<MAXN> possible[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    vector<pair<int, int>> edges(M);
    for (int i = 0; i < M; i++) {
        cin >> edges[i].first >> edges[i].second;
    }
    for (int i = 0; i < N; i++) {
        possible[i].set();
        possible[i][i] = 0;
    }
    int queries = 0;
    srand(time(NULL));
    while (true) {
        long long total = 0;
        for (int a = 0; a < N; a++) {
            total += possible[a].count();
        }
        if (total <= 1) {
            int foundA = -1, foundB = -1;
            for (int a = 0; a < N; a++) {
                if (possible[a].count() == 1) {
                    for (int b = 0; b < N; b++) {
                        if (possible[a][b]) {
                            foundB = b;
                            foundA = a;
                            break;
                        }
                    }
                }
            }
            cout << 1 << " " << foundA << " " << foundB << endl;
            cout.flush();
            return 0;
        }
        long long half = total / 2;
        vector<int> best_perm;
        long long best_diff = LLONG_MAX;
        for (int trial = 0; trial < 5; trial++) {
            vector<int> perm(N);
            iota(perm.begin(), perm.end(), 0);
            srand(queries * 10007 + trial);
            random_shuffle(perm.begin(), perm.end());
            vector<int> rnk(N);
            for (int i = 0; i < N; i++) {
                rnk[perm[i]] = i;
            }
            vector<vector<int>> adjj(N);
            for (auto [u, v] : edges) {
                if (rnk[u] < rnk[v]) {
                    adjj[u].push_back(v);
                } else {
                    adjj[v].push_back(u);
                }
            }
            vector<bitset<MAXN>> re(N);
            for (int j = N - 1; j >= 0; j--) {
                int u = perm[j];
                re[u].reset();
                re[u][u] = 1;
                for (int vv : adjj[u]) {
                    re[u] |= re[vv];
                }
            }
            long long num1 = 0;
            for (int a = 0; a < N; a++) {
                bitset<MAXN> inter = possible[a] & re[a];
                num1 += inter.count();
            }
            long long diff = abs(num1 * 2LL - total);
            if (diff < best_diff) {
                best_diff = diff;
                best_perm = perm;
            }
        }
        vector<int> perm = best_perm;
        vector<int> rnk(N);
        for (int i = 0; i < N; i++) {
            rnk[perm[i]] = i;
        }
        vector<int> choice(M);
        for (int i = 0; i < M; i++) {
            int u = edges[i].first, v = edges[i].second;
            choice[i] = (rnk[u] < rnk[v]) ? 0 : 1;
        }
        cout << 0;
        for (int c : choice) {
            cout << " " << c;
        }
        cout << endl;
        cout.flush();
        int x;
        cin >> x;
        queries++;
        vector<vector<int>> adjj(N);
        for (int i = 0; i < M; i++) {
            int u = edges[i].first, v = edges[i].second;
            if (choice[i] == 0) {
                adjj[u].push_back(v);
            } else {
                adjj[v].push_back(u);
            }
        }
        vector<bitset<MAXN>> re(N);
        for (int j = N - 1; j >= 0; j--) {
            int u = perm[j];
            re[u].reset();
            re[u][u] = 1;
            for (int vv : adjj[u]) {
                re[u] |= re[vv];
            }
        }
        for (int a = 0; a < N; a++) {
            if (possible[a].any()) {
                if (x == 1) {
                    possible[a] &= re[a];
                } else {
                    possible[a] &= ~re[a];
                }
                possible[a][a] = 0;
            }
        }
    }
    return 0;
}