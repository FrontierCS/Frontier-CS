#include <bits/stdc++.h>
using namespace std;

static const long long RATE_BUDGET = 3000000;

struct State {
    int h, r, a, b, P, k;
    int c1s, c1v, c2s, c2v;
    vector<pair<int,int>> board;
};

bool readState(State &st) {
    // STATE h r a b P k
    if (!(cin >> st.h)) return false;
    if (st.h == -1) return false;
    if (!(cin >> st.r >> st.a >> st.b >> st.P >> st.k)) return false;
    string tok;
    if (!(cin >> tok)) return false;
    if (tok == "-1") return false;
    if (tok != "ALICE") return false;
    if (!(cin >> st.c1s >> st.c1v >> st.c2s >> st.c2v)) return false;
    if (!(cin >> tok)) return false;
    if (tok == "-1") return false;
    if (tok != "BOARD") return false;
    st.board.clear();
    for (int i = 0; i < st.k; ++i) {
        int s, v;
        if (!(cin >> s >> v)) return false;
        st.board.emplace_back(s, v);
    }
    return true;
}

bool readUntilRates(double &w, double &d) {
    string tok;
    while (cin >> tok) {
        if (tok == "-1") return false;
        if (tok == "RATES") {
            if (!(cin >> w >> d)) return false;
            return true;
        }
        // Consume any unexpected tokens (should not happen here)
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int G;
    if (!(cin >> G)) return 0;
    if (G == -1) return 0;

    long long used_rate = 0;

    string tok;
    while (cin >> tok) {
        if (tok == "-1") break;

        if (tok == "STATE") {
            State st;
            cin.putback('\n'); // Putback a newline to allow readState to read numbers correctly
            // Workaround: we already consumed "STATE", so read remaining fields directly
            // We'll manually parse since readState expects "STATE" already processed.
            if (!(cin >> st.h)) break;
            if (st.h == -1) break;
            if (!(cin >> st.r >> st.a >> st.b >> st.P >> st.k)) break;
            string tok2;
            if (!(cin >> tok2)) break;
            if (tok2 == "-1") break;
            if (tok2 != "ALICE") break;
            if (!(cin >> st.c1s >> st.c1v >> st.c2s >> st.c2v)) break;
            if (!(cin >> tok2)) break;
            if (tok2 == "-1") break;
            if (tok2 != "BOARD") break;
            st.board.clear();
            for (int i = 0; i < st.k; ++i) {
                int s, v;
                if (!(cin >> s >> v)) return 0;
                st.board.emplace_back(s, v);
            }

            // Decide action
            if (st.r == 4 || st.a <= 0) {
                cout << "ACTION CHECK" << endl;
                continue;
            }

            int t = 100; // per-state RATE budget: 100 preflop, 100 flop, 100 turn = 300 per hand
            // Ensure not exceeding budget
            if (used_rate + t > RATE_BUDGET) t = max(0LL, RATE_BUDGET - used_rate);
            double w = 0.5, d = 0.0;
            if (t > 0) {
                cout << "RATE " << t << endl;
                cout.flush();
                if (!readUntilRates(w, d)) return 0;
                used_rate += t;
            }
            double e = w + d * 0.5;

            double margin = 0.03;
            if (st.r == 1) margin = 0.03;
            else if (st.r == 2) margin = 0.03;
            else if (st.r == 3) margin = 0.04;

            if (e >= 0.5 + margin && st.a > 0) {
                int x = st.a;
                if (x < 1) x = 1;
                cout << "ACTION RAISE " << x << endl;
            } else {
                cout << "ACTION CHECK" << endl;
            }
        } else if (tok == "OPP") {
            string what;
            if (!(cin >> what)) break;
            if (what == "-1") break;
            if (what == "CHECK") {
                // nothing
            } else if (what == "FOLD") {
                // nothing
            } else if (what == "CALL") {
                int x;
                if (!(cin >> x)) break;
                // nothing
            } else {
                // unknown
            }
        } else if (tok == "RESULT") {
            int delta;
            if (!(cin >> delta)) break;
            // nothing
        } else if (tok == "SCORE") {
            double W;
            if (!(cin >> W)) break;
            // End of match
            break;
        } else if (tok == "RATES") {
            // Should be handled inside readUntilRates; consume if appears
            double w, d;
            if (!(cin >> w >> d)) break;
        } else if (tok == "ALICE" || tok == "BOARD") {
            // Should only appear within STATE parsing; consume expected tokens conservatively
            // Try to skip reasonable numbers to resync
            if (tok == "ALICE") {
                int s1,v1,s2,v2;
                if (!(cin >> s1 >> v1 >> s2 >> v2)) break;
            } else {
                // BOARD, need to skip variable amount; but without k we cannot know; ignore
            }
        } else {
            // Unknown token; ignore
        }
    }
    return 0;
}