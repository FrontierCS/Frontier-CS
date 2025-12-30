#include <bits/stdc++.h>
using namespace std;

static long long RATE_BUDGET = 3000000;

struct State {
    int h, r, a, b, P, k;
    int as1, av1, as2, av2;
    vector<pair<int,int>> board;
};

bool askRates(int t, double &w, double &d) {
    if (t <= 0 || RATE_BUDGET <= 0) return false;
    if (t > RATE_BUDGET) t = (int)RATE_BUDGET;
    cout << "RATE " << t << endl;
    cout.flush();
    RATE_BUDGET -= t;

    string tok;
    if (!(cin >> tok)) exit(0);
    if (tok == "-1") exit(0);
    if (tok != "RATES") {
        // Unexpected token, try to resync (should not happen)
        // Consume until we find RATES
        while (tok != "RATES") {
            if (!(cin >> tok)) exit(0);
            if (tok == "-1") exit(0);
        }
    }
    if (!(cin >> w >> d)) exit(0);
    return true;
}

bool strongPreflopHeuristic(int v1, int v2, int s1, int s2) {
    // Fallback if out of RATE budget: simple aggressive heuristic.
    // Values: 1..13 represent 2..A
    bool pair = (v1 == v2);
    bool suited = (s1 == s2);
    int hi = max(v1, v2);
    int lo = min(v1, v2);

    // Map 1..13 to 2..A; high cards are large v
    // Aggressive with strong pairs and big broadways
    if (pair) {
        if (v1 >= 9) return true;        // 10-10+ (since 1->2, 9->10)
        if (v1 >= 7 && suited) return true; // 8-8 suited (arbitrary small boost)
        return false;
    }
    // Big slicks and broadways
    if (hi >= 12 && lo >= 10) return true; // Q-T+ (Q/T, K/T, A/T)
    if (hi >= 13 && lo >= 11 && suited) return true; // KJ+ suited
    if (hi == 13 && lo >= 9) return true; // K9+ (rough)
    if (hi == 14 && lo >= 9) return true; // A9+
    // Suited connectors medium+
    if (suited && hi - lo == 1 && hi >= 9) return true; // T9s, JTs, QJs, KQs
    return false;
}

string decideAction(const State &st) {
    // Never fold (CHECK dominates since Bob checks back)
    if (st.a <= 0) {
        return "ACTION CHECK";
    }

    // Desired sample counts per round (keep within budget)
    int tWanted = 0;
    if (st.r == 1) tWanted = 100;
    else if (st.r == 2) tWanted = 80;
    else if (st.r == 3) tWanted = 60;
    else if (st.r == 4) tWanted = 40;

    double w = 0.0, d = 0.0;
    bool gotRates = false;
    if (RATE_BUDGET > 0 && tWanted > 0) {
        int t = (int)min<long long>(tWanted, RATE_BUDGET);
        if (t >= 10) gotRates = askRates(t, w, d);
    }

    double s = 0.0;
    if (gotRates) {
        s = 2.0 * w + d;
    } else {
        // Fallback: only use a preflop heuristic; otherwise default to CHECK
        if (st.r == 1) {
            if (strongPreflopHeuristic(st.av1, st.av2, st.as1, st.as2)) {
                int x = st.a;
                return string("ACTION RAISE ") + to_string(x);
            } else {
                return "ACTION CHECK";
            }
        } else {
            return "ACTION CHECK";
        }
    }

    // Thresholds per round (s = 2w + d)
    double thr = 1.04; // default
    if (st.r == 1) thr = 1.10;
    else if (st.r == 2) thr = 1.08;
    else if (st.r == 3) thr = 1.06;
    else if (st.r == 4) thr = 1.04;

    if (s >= thr) {
        int x = st.a; // shove maximizes EV if called when s>1
        if (x < 1) return "ACTION CHECK";
        return string("ACTION RAISE ") + to_string(x);
    } else {
        return "ACTION CHECK";
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string tok;
    if (!(cin >> tok)) return 0;
    if (tok == "-1") return 0;
    int G = 0;
    {
        // tok should be the integer G
        // If it's not an integer, try to parse it as integer; otherwise exit.
        try {
            G = stoi(tok);
        } catch (...) {
            // Unexpected; exit gracefully
            return 0;
        }
    }

    while (cin >> tok) {
        if (tok == "-1") {
            return 0;
        } else if (tok == "STATE") {
            State st;
            if (!(cin >> st.h >> st.r >> st.a >> st.b >> st.P >> st.k)) return 0;
            string tok2;
            if (!(cin >> tok2)) return 0;
            if (tok2 == "-1") return 0;
            if (tok2 != "ALICE") {
                // Malformed, try to continue
                return 0;
            }
            if (!(cin >> st.as1 >> st.av1 >> st.as2 >> st.av2)) return 0;

            string tok3;
            if (!(cin >> tok3)) return 0;
            if (tok3 == "-1") return 0;
            if (tok3 != "BOARD") {
                return 0;
            }
            st.board.clear();
            for (int i = 0; i < st.k; i++) {
                int s, v;
                if (!(cin >> s >> v)) return 0;
                st.board.emplace_back(s, v);
            }

            string action = decideAction(st);
            cout << action << endl;
            cout.flush();
        } else if (tok == "OPP") {
            string what;
            if (!(cin >> what)) return 0;
            if (what == "CALL") {
                int x; if (!(cin >> x)) return 0;
            } else if (what == "CHECK") {
                // nothing
            } else if (what == "FOLD") {
                // nothing
            } else {
                // unknown
            }
        } else if (tok == "RATES") {
            // Should normally be handled immediately after RATE queries.
            // Read and discard to stay in sync if it appears here.
            double w, d;
            if (!(cin >> w >> d)) return 0;
        } else if (tok == "RESULT") {
            int delta;
            if (!(cin >> delta)) return 0;
            // No action needed
        } else if (tok == "SCORE") {
            double W;
            if (!(cin >> W)) return 0;
            // End of match
            break;
        } else if (tok == "ALICE" || tok == "BOARD") {
            // Should be parsed within STATE, but guard anyway
            // Consume rest of line cautiously
        } else {
            // Unknown token, ignore gracefully
        }
    }
    return 0;
}