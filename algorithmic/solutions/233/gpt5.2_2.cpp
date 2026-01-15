#include <bits/stdc++.h>
using namespace std;

static inline bool isNumericToken(const string& s) {
    if (s.empty()) return false;
    size_t i = 0;
    if (s[0] == '-') i = 1;
    if (i >= s.size()) return false;
    for (; i < s.size(); i++) if (!isdigit((unsigned char)s[i])) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n, m;
        cin >> n >> m;

        vector<vector<int>> g(n + 1, vector<int>(n + 1));
        for (int i = 1; i <= n; i++) {
            for (int j = 1; j <= n; j++) cin >> g[i][j];
        }

        priority_queue<int> pq; // keep m smallest
        auto pushSmall = [&](int v) {
            if ((int)pq.size() < m) pq.push(v);
            else if (v < pq.top()) {
                pq.pop();
                pq.push(v);
            }
        };

        string tok;
        if (!(cin >> tok)) {
            // No further data: cannot proceed in non-interactive environment
            // Output nothing to avoid undefined behavior.
            return 0;
        }

        if (!isNumericToken(tok)) {
            // Format B: n move strings (for snakes of lengths 1..n), then compute all f(l,T)
            vector<string> moves(n);
            moves[0] = tok;
            for (int i = 1; i < n; i++) cin >> moves[i];

            int totalTimes = 2 * n - 1;
            int totalMoves = 2 * n - 2;

            for (int l = 1; l <= n; l++) {
                string mv = moves[l - 1];
                vector<char> seq;
                if ((int)mv.size() == totalMoves) {
                    seq.assign(mv.begin(), mv.end());
                } else if ((int)mv.size() == totalMoves - 1) {
                    seq.reserve(totalMoves);
                    seq.push_back('D');
                    for (char c : mv) seq.push_back(c);
                } else {
                    seq.reserve(totalMoves);
                    for (int i = 0; i < totalMoves && i < (int)mv.size(); i++) seq.push_back(mv[i]);
                    while ((int)seq.size() < totalMoves) seq.push_back('D');
                }

                deque<pair<int,int>> body;
                multiset<int> ms;

                for (int i = 1; i <= l; i++) {
                    body.push_back({1, i});
                    ms.insert(g[1][i]);
                }
                pushSmall(*ms.rbegin());

                int hx = 1, hy = 1;
                for (int step = 0; step < totalMoves; step++) {
                    auto [tx, ty] = body.back();
                    body.pop_back();
                    auto it = ms.find(g[tx][ty]);
                    if (it != ms.end()) ms.erase(it);

                    char c = seq[step];
                    if (c == 'D') hx++;
                    else hy++;

                    body.push_front({hx, hy});
                    ms.insert(g[hx][hy]);

                    pushSmall(*ms.rbegin());
                }

                (void)totalTimes;
            }
        } else {
            // Format A: directly given all f(l,T) values: n*(2n-1) integers (in any order), take m smallest
            long long total = 1LL * n * (2LL * n - 1);
            pushSmall(stoi(tok));
            for (long long i = 1; i < total; i++) {
                int v;
                cin >> v;
                pushSmall(v);
            }
        }

        vector<int> ans;
        ans.reserve(m);
        while (!pq.empty()) {
            ans.push_back(pq.top());
            pq.pop();
        }
        sort(ans.begin(), ans.end());
        for (int i = 0; i < (int)ans.size(); i++) {
            if (i) cout << ' ';
            cout << ans[i];
        }
        cout << "\n";
    }

    return 0;
}