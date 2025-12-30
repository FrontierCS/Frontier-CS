#include <bits/stdc++.h>
using namespace std;

static inline void appendInt(string &s, int x) {
    char buf[12];
    int p = 0;
    while (x > 0) {
        buf[p++] = char('0' + (x % 10));
        x /= 10;
    }
    for (int i = p - 1; i >= 0; --i) s.push_back(buf[i]);
}

struct Solver {
    int n;
    vector<uint8_t> dpC, dpL, newC, newL;
    vector<int> prefAll, prefC;

    int askPrefix(int m) {
        static string out;
        out.clear();
        out.reserve((size_t)(m + 4) * 7);

        out.push_back('?');
        out.push_back(' ');
        appendInt(out, m);
        for (int i = 1; i <= m; ++i) {
            out.push_back(' ');
            appendInt(out, i);
        }
        out.push_back('\n');

        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);

        char resp[8];
        if (scanf("%7s", resp) != 1) exit(0);
        return resp[0] == 'Y'; // YES
    }

    bool makeGuess(int g) {
        static string out;
        out.clear();
        out.reserve(32);
        out.push_back('!');
        out.push_back(' ');
        appendInt(out, g);
        out.push_back('\n');

        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);

        char resp[8];
        if (scanf("%7s", resp) != 1) exit(0);
        return resp[0] == ':' && resp[1] == ')';
    }

    void update(int m, int ansYes) {
        fill(newC.begin(), newC.end(), 0);
        fill(newL.begin(), newL.end(), 0);

        if (ansYes) {
            for (int i = 1; i <= m; ++i) newC[i] = dpC[i] | dpL[i];
            for (int i = m + 1; i <= n; ++i) newL[i] = dpC[i];
        } else {
            for (int i = 1; i <= m; ++i) newL[i] = dpC[i];
            for (int i = m + 1; i <= n; ++i) newC[i] = dpC[i] | dpL[i];
        }

        dpC.swap(newC);
        dpL.swap(newL);
    }

    void run() {
        if (scanf("%d", &n) != 1) return;

        if (n == 1) {
            makeGuess(1);
            return;
        }

        dpC.assign(n + 1, 1);
        dpL.assign(n + 1, 0);
        newC.assign(n + 1, 0);
        newL.assign(n + 1, 0);
        prefAll.assign(n + 1, 0);
        prefC.assign(n + 1, 0);

        int q = 0;
        while (q < 53) {
            prefAll[0] = 0;
            prefC[0] = 0;
            for (int i = 1; i <= n; ++i) {
                int a = (int)(dpC[i] | dpL[i]);
                prefAll[i] = prefAll[i - 1] + a;
                prefC[i] = prefC[i - 1] + (int)dpC[i];
            }
            int totalAll = prefAll[n];
            int totalC = prefC[n];

            if (totalAll <= 2) break;

            int bestM = -1;
            int bestW = INT_MAX;
            long long bestBal = (1LL << 62);

            for (int m = 1; m <= n - 1; ++m) {
                int prefixAll = prefAll[m];
                if (prefixAll == 0 || prefixAll == totalAll) continue;

                int prefixC = prefC[m];
                int outsideAll = totalAll - prefixAll;
                int outsideC = totalC - prefixC;

                int w1 = prefixAll + outsideC;     // if answer YES
                int w2 = outsideAll + prefixC;     // if answer NO
                int w = max(w1, w2);

                long long bal = llabs(2LL * prefixAll - totalAll);

                if (w < bestW || (w == bestW && bal < bestBal)) {
                    bestW = w;
                    bestBal = bal;
                    bestM = m;
                }
            }

            if (bestM == -1) {
                // Shouldn't happen if totalAll > 2, but fallback.
                bestM = min(n - 1, max(1, n / 2));
            }

            int ansYes = askPrefix(bestM);
            ++q;
            update(bestM, ansYes);
        }

        vector<int> cand;
        cand.reserve(4);
        for (int i = 1; i <= n; ++i) {
            if (dpC[i] | dpL[i]) cand.push_back(i);
        }
        if (cand.empty()) cand.push_back(1);

        if (cand.size() == 1) {
            makeGuess(cand[0]);
            return;
        }

        if (makeGuess(cand[0])) return;
        makeGuess(cand[1]);
    }
};

int main() {
    Solver s;
    s.run();
    return 0;
}