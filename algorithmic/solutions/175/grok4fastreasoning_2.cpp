#include <bits/stdc++.h>
using namespace std;

long long compute_score_and_deltas(vector<char>& assign, vector<int>& del, const vector<array<int, 3>>& clauses) {
    long long sc = 0;
    fill(del.begin(), del.end(), 0);
    for (size_t i = 0; i < clauses.size(); ++i) {
        const auto& cl = clauses[i];
        int aa = abs(cl[0]), bb = abs(cl[1]), cc = abs(cl[2]);
        bool la = (cl[0] > 0 ? assign[aa] : !assign[aa]);
        bool lb = (cl[1] > 0 ? assign[bb] : !assign[bb]);
        bool lc = (cl[2] > 0 ? assign[cc] : !assign[cc]);
        int num = (la ? 1 : 0) + (lb ? 1 : 0) + (lc ? 1 : 0);
        if (num > 0) ++sc;
        if (num == 0) {
            ++del[aa];
            ++del[bb];
            ++del[cc];
        } else if (num == 1) {
            if (la) --del[aa];
            else if (lb) --del[bb];
            else --del[cc];
        }
    }
    return sc;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    srand((unsigned)time(NULL));
    int n, m;
    cin >> n >> m;
    vector<array<int, 3>> clauses(m);
    vector<vector<int>> clauses_per_var(n + 1);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        clauses_per_var[abs(a)].push_back(i);
        clauses_per_var[abs(b)].push_back(i);
        clauses_per_var[abs(c)].push_back(i);
    }
    vector<char> best_assign(n + 1, 0);
    long long best_score = -1LL;
    int num_trials = 5;
    for (int trial = 0; trial < num_trials; ++trial) {
        vector<char> assign(n + 1);
        for (int i = 1; i <= n; ++i) {
            assign[i] = (rand() % 2);
        }
        vector<int> del(n + 1, 0);
        long long score = compute_score_and_deltas(assign, del, clauses);
        while (true) {
            int best_v = -1;
            int max_d = 0;
            for (int v = 1; v <= n; ++v) {
                if (del[v] > max_d) {
                    max_d = del[v];
                    best_v = v;
                }
            }
            if (max_d <= 0) break;
            score += max_d;
            for (int cid : clauses_per_var[best_v]) {
                const auto& cl = clauses[cid];
                int aa = abs(cl[0]), ab = abs(cl[1]), ac = abs(cl[2]);
                bool la = (cl[0] > 0 ? assign[aa] : !assign[aa]);
                bool lb = (cl[1] > 0 ? assign[ab] : !assign[ab]);
                bool lc = (cl[2] > 0 ? assign[ac] : !assign[ac]);
                int num = (la ? 1 : 0) + (lb ? 1 : 0) + (lc ? 1 : 0);
                if (num == 0) {
                    del[aa] -= 1;
                    del[ab] -= 1;
                    del[ac] -= 1;
                } else if (num == 1) {
                    if (la) {
                        del[aa] += 1;
                    } else if (lb) {
                        del[ab] += 1;
                    } else {
                        del[ac] += 1;
                    }
                }
            }
            assign[best_v] = 1 - assign[best_v];
            for (int cid : clauses_per_var[best_v]) {
                const auto& cl = clauses[cid];
                int aa = abs(cl[0]), ab = abs(cl[1]), ac = abs(cl[2]);
                bool la = (cl[0] > 0 ? assign[aa] : !assign[aa]);
                bool lb = (cl[1] > 0 ? assign[ab] : !assign[ab]);
                bool lc = (cl[2] > 0 ? assign[ac] : !assign[ac]);
                int num = (la ? 1 : 0) + (lb ? 1 : 0) + (lc ? 1 : 0);
                if (num == 0) {
                    del[aa] += 1;
                    del[ab] += 1;
                    del[ac] += 1;
                } else if (num == 1) {
                    if (la) {
                        del[aa] -= 1;
                    } else if (lb) {
                        del[ab] -= 1;
                    } else {
                        del[ac] -= 1;
                    }
                }
            }
        }
        if (score > best_score) {
            best_score = score;
            best_assign = assign;
        }
    }
    for (int i = 1; i <= n; ++i) {
        cout << (int)best_assign[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}