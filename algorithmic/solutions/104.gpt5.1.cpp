#include <bits/stdc++.h>
using namespace std;

struct Node {
    int len;   // current run length of last honesty bit (0,1,2). 3 means dead but we instantly kill.
    int last;  // last honesty bit (0 or 1), valid only if len>0
    int code;  // encoded state 0..4, valid only if alive
    bool alive;
};

bool aliveAfter[5][2][2]; // [state][s][y]

int encode_state(int len, int last) {
    if (len == 0) return 0;
    if (len == 1) return last == 0 ? 1 : 2;
    // len == 2
    return last == 0 ? 3 : 4;
}

void process_query(vector<Node> &a, int n, int l, int r, int y, int &aliveCount) {
    for (int i = 1; i <= n; ++i) {
        Node &nd = a[i];
        if (!nd.alive) continue;
        int s = (i >= l && i <= r) ? 1 : 0;
        int h = s ^ y;
        if (nd.len == 0) {
            nd.len = 1;
            nd.last = h;
            nd.code = (h == 0 ? 1 : 2);
        } else {
            if (nd.last == h) {
                nd.len++;
                if (nd.len >= 3) {
                    nd.alive = false;
                    nd.len = 0;
                    nd.code = 0;
                    --aliveCount;
                } else {
                    // len == 2
                    nd.code = (h == 0 ? 3 : 4);
                }
            } else {
                nd.len = 1;
                nd.last = h;
                nd.code = (h == 0 ? 1 : 2);
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Precompute aliveAfter table
    for (int st = 0; st < 5; ++st) {
        int len, bit;
        if (st == 0)       { len = 0; bit = 0; }
        else if (st == 1)  { len = 1; bit = 0; }
        else if (st == 2)  { len = 1; bit = 1; }
        else if (st == 3)  { len = 2; bit = 0; }
        else               { len = 2; bit = 1; }
        for (int s = 0; s <= 1; ++s) {
            for (int y = 0; y <= 1; ++y) {
                int h = s ^ y;
                bool ok;
                if (len == 0) {
                    ok = true;
                } else if (bit == h) {
                    if (len == 2) ok = false;
                    else ok = true; // len ==1 -> becomes 2
                } else {
                    ok = true;
                }
                aliveAfter[st][s][y] = ok;
            }
        }
    }

    int T;
    if (!(cin >> T)) {
        return 0;
    }
    const double base = 1.116;

    while (T--) {
        int n;
        cin >> n;

        int maxQueries = (int)ceil(log((double)n) / log(base));
        maxQueries *= 2;

        vector<Node> a(n + 1);
        for (int i = 1; i <= n; ++i) {
            a[i].len = 0;
            a[i].last = 0;
            a[i].code = 0;
            a[i].alive = true;
        }
        int aliveCount = n;
        int queriesUsed = 0;

        // Predetermined first two queries to diversify membership patterns
        vector<pair<int,int>> pre;
        int mid = n / 2;
        if (mid >= 1) {
            pre.push_back({1, mid});
            if (mid + 1 <= n)
                pre.push_back({mid + 1, n});
        }

        for (auto qr : pre) {
            if (queriesUsed >= maxQueries || aliveCount <= 2) break;
            int l = qr.first, r = qr.second;
            if (l > r) continue;
            cout << "? " << l << " " << r << '\n';
            cout.flush();
            int x;
            if (!(cin >> x)) return 0;
            int k = r - l + 1;
            int y = x - (k - 1); // 0 or 1
            ++queriesUsed;
            process_query(a, n, l, r, y, aliveCount);
        }

        // Main loop using prefix queries selected by DP
        while (aliveCount > 2 && queriesUsed < maxQueries) {
            long long TOT[5] = {0,0,0,0,0};
            for (int i = 1; i <= n; ++i) {
                if (!a[i].alive) continue;
                TOT[a[i].code]++;
            }

            long long S0 = 0, S1 = 0;
            for (int st = 0; st < 5; ++st) {
                if (aliveAfter[st][0][0]) S0 += TOT[st];
                if (aliveAfter[st][0][1]) S1 += TOT[st];
            }

            long long bestW = (1LL << 60);
            int bestR = 1;
            long long curS0 = S0, curS1 = S1;

            for (int r = 1; r <= n; ++r) {
                if (a[r].alive) {
                    int st = a[r].code;
                    curS0 += (int)aliveAfter[st][1][0] - (int)aliveAfter[st][0][0];
                    curS1 += (int)aliveAfter[st][1][1] - (int)aliveAfter[st][0][1];
                }
                long long W = (curS0 > curS1) ? curS0 : curS1;
                if (W < bestW) {
                    bestW = W;
                    bestR = r;
                }
            }

            cout << "? " << 1 << " " << bestR << '\n';
            cout.flush();
            int x;
            if (!(cin >> x)) return 0;
            int k = bestR; // l=1, r=bestR
            int y = x - (k - 1);
            ++queriesUsed;
            process_query(a, n, 1, bestR, y, aliveCount);
        }

        // Collect remaining candidates
        vector<int> cand;
        for (int i = 1; i <= n; ++i) {
            if (a[i].alive) cand.push_back(i);
        }
        if (cand.empty()) {
            cand.push_back(1);
            if (n >= 2) cand.push_back(2);
        }

        int guesses = 0;
        int yres;

        if (!cand.empty()) {
            cout << "! " << cand[0] << '\n';
            cout.flush();
            if (!(cin >> yres)) return 0;
            ++guesses;
            if (yres == 1) {
                // found absent
            } else if (guesses < 2 && cand.size() >= 2) {
                cout << "! " << cand[1] << '\n';
                cout.flush();
                if (!(cin >> yres)) return 0;
                ++guesses;
                // must be 1 for correct algorithm
            }
        }

        cout << "#\n";
        cout.flush();
    }

    return 0;
}