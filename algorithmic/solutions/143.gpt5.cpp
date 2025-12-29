#include <bits/stdc++.h>
using namespace std;

static const long long TOTAL_RATE_BUDGET = 3000000;

struct State {
    int h, r, a, b, P, k;
    int ac1, av1, ac2, av2;
    vector<pair<int,int>> board;
};

bool readToken(string &tok) {
    if (!(cin >> tok)) return false;
    if (tok == "-1") exit(0);
    return true;
}

void readInt(int &x) {
    string tok;
    if (!readToken(tok)) exit(0);
    x = stoi(tok);
}

pair<double,double> queryRates(int t) {
    cout << "RATE " << t << endl;
    cout.flush();
    string tok;
    if (!readToken(tok)) exit(0);
    if (tok == "RATES") {
        double w, d;
        if (!(cin >> w >> d)) exit(0);
        return {w, d};
    } else if (tok == "-1") {
        exit(0);
    } else {
        // Unexpected token; try to handle gracefully
        // But per protocol, after RATE we should get RATES.
        exit(0);
    }
    return {0.0, 0.0};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int G;
    if (!(cin >> G)) return 0;
    if (G == -1) return 0;

    long long budgetRemaining = TOTAL_RATE_BUDGET;

    string tok;
    while (readToken(tok)) {
        if (tok == "STATE") {
            State st;
            readInt(st.h);
            readInt(st.r);
            readInt(st.a);
            readInt(st.b);
            readInt(st.P);
            readInt(st.k);

            // ALICE line
            string t2;
            readToken(t2); // should be ALICE
            readInt(st.ac1);
            readInt(st.av1);
            readInt(st.ac2);
            readInt(st.av2);

            // BOARD line
            string t3;
            readToken(t3); // "BOARD"
            st.board.clear();
            for (int i = 0; i < st.k; ++i) {
                int cs, vs;
                readInt(cs);
                readInt(vs);
                st.board.emplace_back(cs, vs);
            }

            // Decide action
            if (st.r < 4) {
                cout << "ACTION CHECK" << endl;
                cout.flush();
            } else {
                // River decision
                double w = 0.0, d = 0.0;
                int t = 0;
                if (budgetRemaining > 0) {
                    t = (int)min<long long>(200, budgetRemaining);
                    auto res = queryRates(t);
                    w = res.first; d = res.second;
                    budgetRemaining -= t;
                } else {
                    // No budget left; default to check
                    cout << "ACTION CHECK" << endl;
                    cout.flush();
                    continue;
                }

                double l = max(0.0, 1.0 - w - d);
                double adv = w - l; // = 2w + d - 1

                // Thresholds
                const double adv_min = 0.08; // require decent edge
                if (adv > adv_min) {
                    double numerator = l * st.P + d * (st.P * 0.5);
                    double denom = adv;
                    double x0 = (denom > 1e-12) ? (numerator / denom) : 1e18;
                    // If we can exceed threshold within stack, raise
                    if (x0 <= st.a - 1) {
                        int fudge = max(1, min(10, (int)floor(x0 * 0.15) + 1));
                        long long x = (long long)floor(x0) + fudge;
                        if (x < 1) x = 1;
                        if (x > st.a) x = st.a;
                        // Optional cap to avoid extreme over-commit on noisy edges
                        // Here we do not cap beyond stack.
                        cout << "ACTION RAISE " << x << endl;
                        cout.flush();
                    } else {
                        // Can't exceed threshold; safer to check
                        cout << "ACTION CHECK" << endl;
                        cout.flush();
                    }
                } else {
                    cout << "ACTION CHECK" << endl;
                    cout.flush();
                }
            }
        } else if (tok == "RATES") {
            // Should only appear in response to our queryRates; queryRates consumes it.
            // If we see it here, consume the doubles to stay in sync.
            double w, d;
            if (!(cin >> w >> d)) exit(0);
        } else if (tok == "OPP") {
            string what;
            readToken(what); // CHECK, FOLD, CALL
            if (what == "CALL") {
                int x; readInt(x);
            }
            // else if FOLD or CHECK: nothing more to consume
        } else if (tok == "RESULT") {
            int delta;
            readInt(delta);
            // result consumed
        } else if (tok == "SCORE") {
            double W;
            if (!(cin >> W)) exit(0);
            // match ended
            break;
        } else {
            // Unknown token; consume line or ignore
            // To stay safe, continue.
        }
    }

    return 0;
}