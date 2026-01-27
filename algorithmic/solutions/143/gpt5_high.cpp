#include <bits/stdc++.h>
using namespace std;

static const long long RATE_BUDGET = 3000000;

struct Card { int s, v; };

struct State {
    int h, r, a, b, P, k;
    Card c1, c2;
    vector<Card> board;
};

long long budgetUsed = 0;

bool readToken(string &tok) {
    if (!(cin >> tok)) return false;
    if (tok == "-1") exit(0);
    return true;
}

pair<long double,long double> askRates(int t) {
    cout << "RATE " << t << endl;
    cout.flush();
    string tok;
    while (true) {
        if (!readToken(tok)) return {0.0L, 0.0L};
        if (tok == "RATES") {
            long double w, d;
            cin >> w >> d;
            return {w, d};
        } else if (tok == "-1") {
            exit(0);
        } else {
            // consume rest tokens for unexpected lines, but since protocol guarantees next is RATES, this is safe
            // However, handle other possible lines gracefully
            if (tok == "STATE") {
                // Unexpected per protocol; but consume required tokens to keep stream sane
                State dummy;
                cin >> dummy.h >> dummy.r >> dummy.a >> dummy.b >> dummy.P >> dummy.k;
                string x;
                cin >> x; // ALICE
                int s1,v1,s2,v2;
                cin >> s1 >> v1 >> s2 >> v2;
                cin >> x; // BOARD
                for (int i=0;i<2*dummy.k;i++){int tmp;cin>>tmp;}
            } else if (tok == "OPP") {
                string what; cin >> what;
                if (what == "CALL") { int x; cin >> x; }
            } else if (tok == "RESULT") {
                int delta; cin >> delta;
            } else if (tok == "SCORE") {
                double W; cin >> W;
            } else {
                // consume rest of line? not necessary with operator>>
            }
        }
    }
}

int ceil_div_longdouble(long double num, long double den) {
    if (den <= 0) return INT_MAX/2;
    long double val = num / den;
    long double eps = 1e-12L;
    long long iv = (long long)floor(val + (1.0L - eps));
    while ((long double)iv < val - eps) iv++;
    while ((long double)iv >= val - eps && (long double)(iv-1) >= val - eps) iv--;
    // Ensure ceiling
    if ((long double)iv + eps < val) iv++;
    return (int)iv;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string tok;
    if (!readToken(tok)) return 0;
    int G = stoi(tok);

    // Parameters
    // Base samples per round (1..4)
    int baseSamples[5] = {0, 30, 35, 50, 80};
    int potScale = 15; // add P/potScale
    // Call thresholds per round for raising when cannot force fold
    long double callThresh[5] = {0.0L, 0.10L, 0.06L, 0.05L, 0.02L};
    // Safety margin for opponent's S estimate when trying to force fold
    long double gamma = 0.03L;
    int callSafetyGap = 2;

    while (true) {
        if (!readToken(tok)) break;
        if (tok == "STATE") {
            State st;
            cin >> st.h >> st.r >> st.a >> st.b >> st.P >> st.k;
            string who;
            cin >> who; // ALICE
            cin >> st.c1.s >> st.c1.v >> st.c2.s >> st.c2.v;
            string boardTok;
            cin >> boardTok; // BOARD
            st.board.clear();
            for (int i = 0; i < st.k; ++i) {
                Card c; cin >> c.s >> c.v;
                st.board.push_back(c);
            }

            // Decide rate budget for this state
            int tWanted = baseSamples[st.r] + max(0, st.P / potScale);
            // Ensure we don't exceed global budget
            long long left = RATE_BUDGET - budgetUsed;
            if (left <= 0) tWanted = 0;
            else if ((long long)tWanted > left) tWanted = (int)left;
            pair<long double,long double> rates = {0.0L, 0.0L};
            bool haveRates = false;
            if (tWanted > 0) {
                rates = askRates(tWanted);
                budgetUsed += tWanted;
                haveRates = true;
            }

            // Default action: CHECK
            bool doRaise = false;
            int raiseX = 1;

            if (haveRates) {
                long double w = rates.first;
                long double d = rates.second;
                if (w < 0) w = 0; if (w > 1) w = 1;
                if (d < 0) d = 0; if (d > 1) d = 1;
                long double E = w + 0.5L * d; // our equity for pot share
                long double S = 1.0L - E;     // Bob's pot share for call EV

                if (E > 0.5L) {
                    // Try to force fold with safety margin
                    long double S_eff = S + gamma;
                    if (S_eff >= 0.5L) {
                        // cannot force fold robustly; consider value raise aiming for a call
                        if (E - 0.5L > callThresh[st.r] && st.a >= 1) {
                            long double den = (1.0L - 2.0L * S);
                            if (den <= 1e-15L) {
                                // threshold extremely large or undefined; just small raise
                                raiseX = max(1, min(st.a, 1));
                            } else {
                                long double xth = (S * st.P) / den;
                                int xthInt = (int)ceil(xth - 1e-12L);
                                int xCall = xthInt - callSafetyGap;
                                if (xCall < 1) xCall = 1;
                                if (xCall > st.a) xCall = st.a;
                                raiseX = xCall;
                            }
                            doRaise = (raiseX >= 1);
                        } else {
                            // prefer check
                            doRaise = false;
                        }
                    } else {
                        // We can try to force fold robustly
                        long double den = (1.0L - 2.0L * S_eff);
                        if (den <= 1e-15L) {
                            // Practically any x causes fold; choose minimal
                            raiseX = 1;
                        } else {
                            long double xreq = (S_eff * st.P) / den;
                            int xFoldMin = (int)ceil(xreq - 1e-12L);
                            if (xFoldMin < 1) xFoldMin = 1;
                            if (xFoldMin <= st.a) {
                                raiseX = xFoldMin;
                                doRaise = true;
                            } else {
                                // Cannot force fold; consider value raise aiming for a call
                                if (E - 0.5L > callThresh[st.r] && st.a >= 1) {
                                    // Aim just below non-fudged threshold
                                    long double den2 = (1.0L - 2.0L * S);
                                    if (den2 <= 1e-15L) {
                                        raiseX = max(1, st.a);
                                    } else {
                                        long double xth = (S * st.P) / den2;
                                        int xthInt = (int)ceil(xth - 1e-12L);
                                        int xCall = xthInt - callSafetyGap;
                                        if (xCall < 1) xCall = 1;
                                        if (xCall > st.a) xCall = st.a;
                                        raiseX = xCall;
                                    }
                                    doRaise = (raiseX >= 1);
                                } else {
                                    doRaise = false;
                                }
                            }
                        }
                    }
                } else {
                    // E <= 0.5 -> don't raise
                    doRaise = false;
                }
            } else {
                // No rates left: be conservative
                doRaise = false;
            }

            if (doRaise) {
                if (raiseX < 1) raiseX = 1;
                if (raiseX > st.a) raiseX = st.a;
                cout << "ACTION RAISE " << raiseX << endl;
            } else {
                cout << "ACTION CHECK" << endl;
            }
            cout.flush();
        } else if (tok == "OPP") {
            string what; cin >> what;
            if (what == "CALL") { int x; cin >> x; }
            // If CHECK or FOLD: nothing else here to read
        } else if (tok == "RESULT") {
            int delta; cin >> delta;
        } else if (tok == "SCORE") {
            double W; cin >> W;
            // End of match; continue to read maybe but generally end
        } else if (tok == "RATES") {
            // Unexpected; read and ignore
            long double w,d; cin >> w >> d;
        } else {
            // Unknown token, ignore gracefully
        }
    }
    return 0;
}