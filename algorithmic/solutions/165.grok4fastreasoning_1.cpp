#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const ll INF = 1e18;

int main() {
    int N, M;
    cin >> N >> M;
    int si, sj;
    cin >> si >> sj;
    vector<string> A(N);
    for (int i = 0; i < N; i++) cin >> A[i];
    vector<string> ts(M);
    for (int k = 0; k < M; k++) cin >> ts[k];
    vector<vector<int>> posi(26);
    int NN = N * N;
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) {
        int c = A[i][j] - 'A';
        posi[c].push_back(i * N + j);
    }
    vector<string> current = ts;
    while (current.size() > 1) {
        int best_i = -1, best_j = -1;
        int max_o = -1;
        for (size_t ii = 0; ii < current.size(); ii++) {
            for (size_t jj = 0; jj < current.size(); jj++) {
                if (ii == jj) continue;
                const string& u = current[ii];
                const string& v = current[jj];
                int lu = u.size(), lv = v.size();
                int mo = min(lu, lv);
                for (int o = mo; o >= 0; o--) {
                    bool match = true;
                    if (o > 0) {
                        for (int kk = 0; kk < o; kk++) {
                            if (u[lu - o + kk] != v[kk]) {
                                match = false;
                                break;
                            }
                        }
                    }
                    if (match) {
                        if (o > max_o) {
                            max_o = o;
                            best_i = ii;
                            best_j = jj;
                        }
                        break;
                    }
                }
            }
        }
        int oi = best_i, oj = best_j;
        int o = max_o;
        string news = current[oi] + current[oj].substr(o);
        vector<string> nextc;
        for (size_t k = 0; k < current.size(); k++) {
            if (k != (size_t)oi && k != (size_t)oj) nextc.push_back(current[k]);
        }
        nextc.push_back(news);
        current = std::move(nextc);
    }
    string T = current[0];
    int L = T.size();
    vector<vector<ll>> dist(L + 1, vector<ll>(NN, INF));
    vector<vector<int>> prevp(L + 1, vector<int>(NN, -1));
    int startp = si * N + sj;
    dist[0][startp] = 0;
    for (int k = 1; k <= L; k++) {
        char ch = T[k - 1];
        int cid = ch - 'A';
        const auto& candidates = posi[cid];
        for (int p = 0; p < NN; p++) {
            if (dist[k - 1][p] == INF) continue;
            int pi = p / N, pj = p % N;
            for (int nxt : candidates) {
                int ni = nxt / N, nj = nxt % N;
                ll dcost = abs(ni - pi) + abs(nj - pj) + 1LL;
                ll nc = dist[k - 1][p] + dcost;
                if (nc < dist[k][nxt]) {
                    dist[k][nxt] = nc;
                    prevp[k][nxt] = p;
                }
            }
        }
    }
    ll min_cost = INF;
    int best_e = -1;
    for (int e = 0; e < NN; e++) {
        if (dist[L][e] < min_cost) {
            min_cost = dist[L][e];
            best_e = e;
        }
    }
    vector<pair<int, int>> seq;
    int cur = best_e;
    for (int k = L; k >= 1; k--) {
        int i = cur / N;
        int j = cur % N;
        seq.emplace_back(i, j);
        cur = prevp[k][cur];
    }
    reverse(seq.begin(), seq.end());
    for (auto [i, j] : seq) {
        cout << i << " " << j << "\n";
    }
    return 0;
}