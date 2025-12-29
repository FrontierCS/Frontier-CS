#include <bits/stdc++.h>
using namespace std;

static const int S0 = 0;
static const int S1_0 = 1;
static const int S1_1 = 2;
static const int S2_00 = 3;
static const int S2_01 = 4;
static const int S2_10 = 5;
static const int S2_11 = 6;

struct Solver {
    int n;
    int qmax;
    int qused;

    vector<int> alive;
    vector<uint8_t> st;
    long long cnt[7];

    int nxt[7][2];
    uint8_t can[7][2];

    Solver(int n_) : n(n_), qmax(0), qused(0) {
        st.assign(n + 1, (uint8_t)S0);
        alive.reserve(n);
        for (int i = 1; i <= n; i++) alive.push_back(i);

        memset(cnt, 0, sizeof(cnt));
        cnt[S0] = n;

        buildTransitions();
        computeQmax();
    }

    void buildTransitions() {
        for (int s = 0; s < 7; s++) for (int b = 0; b < 2; b++) nxt[s][b] = -1;

        nxt[S0][0] = S1_0; nxt[S0][1] = S1_1;

        nxt[S1_0][0] = S2_00; nxt[S1_0][1] = S2_01;
        nxt[S1_1][0] = S2_10; nxt[S1_1][1] = S2_11;

        nxt[S2_00][0] = -1;   nxt[S2_00][1] = S2_01;
        nxt[S2_01][0] = S2_10; nxt[S2_01][1] = S2_11;
        nxt[S2_10][0] = S2_00; nxt[S2_10][1] = S2_01;
        nxt[S2_11][0] = S2_10; nxt[S2_11][1] = -1;

        for (int s = 0; s < 7; s++) for (int b = 0; b < 2; b++) can[s][b] = (nxt[s][b] != -1);
    }

    void computeQmax() {
        long double base = 1.116L;
        long double val = 1.0L;
        int k = 0;
        while (val + 1e-18L < (long double)n) {
            val *= base;
            k++;
            if (k > 1000000) break;
        }
        qmax = 2 * k;
    }

    pair<int,int> chooseQuery() {
        int l = alive.front();
        long long total0 = 0, total1 = 0;
        for (int s = 0; s < 7; s++) {
            total0 += cnt[s] * (long long)can[s][0];
            total1 += cnt[s] * (long long)can[s][1];
        }

        long long inside0 = 0, inside1 = 0;
        long long bestWorst = (1LL<<62);
        int bestR = alive.front();

        for (int idx = 0; idx < (int)alive.size(); idx++) {
            int p = alive[idx];

            int r_before = p - 1;
            if (r_before >= l) {
                long long rem0 = inside1 + (total0 - inside0);
                long long rem1 = inside0 + (total1 - inside1);
                long long worst = max(rem0, rem1);
                if (worst < bestWorst) {
                    bestWorst = worst;
                    bestR = r_before;
                }
            }

            int s = st[p];
            inside0 += can[s][0];
            inside1 += can[s][1];

            int r_after = p;
            {
                long long rem0 = inside1 + (total0 - inside0);
                long long rem1 = inside0 + (total1 - inside1);
                long long worst = max(rem0, rem1);
                if (worst < bestWorst) {
                    bestWorst = worst;
                    bestR = r_after;
                }
            }
        }

        if (bestR < l) bestR = l;
        if (bestR > n) bestR = n;
        return {l, bestR};
    }

    int ask(int l, int r) {
        cout << "? " << l << " " << r << "\n";
        cout.flush();
        long long x;
        if (!(cin >> x)) exit(0);
        if (x < 0) exit(0);
        long long len = (long long)r - l + 1;
        int b = (x == len - 1) ? 1 : 0;
        return b;
    }

    void applyAnswer(int l, int r, int b) {
        vector<int> newAlive;
        newAlive.reserve(alive.size());
        long long newCnt[7];
        memset(newCnt, 0, sizeof(newCnt));

        for (int p : alive) {
            int inRange = (l <= p && p <= r) ? 1 : 0;
            int lie = b ^ inRange;
            int ns = nxt[st[p]][lie];
            if (ns != -1) {
                st[p] = (uint8_t)ns;
                newAlive.push_back(p);
                newCnt[ns]++;
            }
        }
        alive.swap(newAlive);
        for (int s = 0; s < 7; s++) cnt[s] = newCnt[s];
    }

    void guessAndFinish() {
        if (alive.empty()) {
            cout << "! 1\n";
            cout.flush();
            int y;
            if (!(cin >> y)) exit(0);
            if (y == 0) {
                cout << "! 2\n";
                cout.flush();
                if (!(cin >> y)) exit(0);
            }
            cout << "#\n";
            cout.flush();
            return;
        }

        cout << "! " << alive[0] << "\n";
        cout.flush();
        int y;
        if (!(cin >> y)) exit(0);
        if (y < 0) exit(0);
        if (y == 0 && alive.size() >= 2) {
            cout << "! " << alive[1] << "\n";
            cout.flush();
            if (!(cin >> y)) exit(0);
            if (y < 0) exit(0);
        }
        cout << "#\n";
        cout.flush();
    }

    void run() {
        while ((int)alive.size() > 2 && qused < qmax) {
            auto [l, r] = chooseQuery();
            int b = ask(l, r);
            applyAnswer(l, r, b);
            qused++;
        }
        guessAndFinish();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        Solver solver(n);
        solver.run();
    }
    return 0;
}