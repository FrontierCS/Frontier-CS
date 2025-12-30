#include <bits/stdc++.h>
using namespace std;

struct State {
    long long h, r, a, b, P, k;
    int c1, v1, c2, v2;
    vector<pair<int,int>> board;
};

static const long long RATE_BUDGET_TOTAL = 3000000;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string first;
    if (!(cin >> first)) return 0;
    if (first == "-1") return 0;
    long long G = stoll(first);

    long long usedTotal = 0;
    long long currentHand = 0;
    long long usedInThisHand = 0;

    auto ask_rate = [&](long long t, double &w, double &d)->bool{
        if (t <= 0) return false;
        cout << "RATE " << t << endl;
        cout.flush();
        usedTotal += t;
        usedInThisHand += t;
        string tok;
        if (!(cin >> tok)) return false;
        if (tok == "-1") exit(0);
        if (tok != "RATES") {
            // Unexpected token; try to recover by reading until we find RATES
            // But per protocol, RATES must come immediately; if not, exit.
            return false;
        }
        if (!(cin >> w >> d)) return false;
        return true;
    };

    auto compute_raise = [&](double e, long long P, long long a)->long long {
        if (a <= 0) return 0;
        if (e <= 0.5) return 0;
        double denom = 2.0*e - 1.0;
        if (denom <= 1e-12) return 0;
        double req = P * (1.0 - e) / denom;
        long long x = (long long)floor(req + 1.0); // minimal integer > req
        if (x < 1) x = 1;
        if (x > a) x = a;
        return x;
    };

    // Base desired samples per round (r=1..4)
    int baseWanted[5] = {0, 60, 90, 120, 160};

    while (true) {
        string tok;
        if (!(cin >> tok)) break;
        if (tok == "-1") {
            return 0;
        } else if (tok == "STATE") {
            State st;
            cin >> st.h >> st.r >> st.a >> st.b >> st.P >> st.k;
            string s;
            cin >> s; // ALICE
            if (s == "-1") return 0;
            cin >> st.c1 >> st.v1 >> st.c2 >> st.v2;
            string sb;
            cin >> sb; // BOARD
            if (sb == "-1") return 0;
            st.board.clear();
            for (int i = 0; i < st.k; i++) {
                int cs, vs;
                cin >> cs >> vs;
                st.board.emplace_back(cs, vs);
            }

            if (st.r == 1 || st.h != currentHand) {
                currentHand = st.h;
                usedInThisHand = 0;
            }

            // Determine how many samples we can spend now
            long long handsRemaining = max(0LL, G - st.h + 1);
            long long remainingBudget = RATE_BUDGET_TOTAL - usedTotal;
            long long perHandLimit = (handsRemaining > 0 ? remainingBudget / handsRemaining : remainingBudget);
            if (perHandLimit < 0) perHandLimit = 0;
            long long allowThisHandRemaining = max(0LL, perHandLimit - usedInThisHand);
            int wanted = baseWanted[min(4LL, st.r)];
            long long t = min<long long>(wanted, min(allowThisHandRemaining, remainingBudget));

            double e = 0.5; // default if we cannot query
            if (t > 0) {
                double w = 0.0, d = 0.0;
                if (!ask_rate(t, w, d)) {
                    return 0;
                }
                e = w + 0.5 * d;
            }

            long long x = compute_raise(e, st.P, st.a);
            if (st.a <= 0) {
                cout << "ACTION CHECK" << endl;
                cout.flush();
            } else if (x <= 0) {
                cout << "ACTION CHECK" << endl;
                cout.flush();
            } else {
                cout << "ACTION RAISE " << x << endl;
                cout.flush();
            }
        } else if (tok == "OPP") {
            string what;
            cin >> what;
            if (what == "-1") return 0;
            if (what == "FOLD") {
                // nothing to read more
            } else if (what == "CALL") {
                long long x;
                cin >> x;
            } else if (what == "CHECK") {
                // nothing else
            }
        } else if (tok == "RESULT") {
            long long delta;
            cin >> delta;
            // Hand ended
            usedInThisHand = 0;
        } else if (tok == "SCORE") {
            double W;
            cin >> W;
            break;
        } else if (tok == "RATES") {
            // Should be handled in ask_rate; but if appears here, read and ignore
            double w, d;
            cin >> w >> d;
        } else {
            // Unknown token, attempt to continue
        }
    }

    return 0;
}