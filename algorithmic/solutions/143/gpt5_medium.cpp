#include <bits/stdc++.h>
using namespace std;

struct Card {
    int suit; // 0..3
    int rank; // 2..14 (2..A)
};

static const long long RATE_BUDGET = 3000000LL;
static long long used_budget = 0;

bool readTokenOrExit(string &tok) {
    if (!(cin >> tok)) return false;
    if (tok == "-1") exit(0);
    return true;
}

bool query_rates(int t, double &w, double &d) {
    if (t <= 0) return false;
    long long rem = RATE_BUDGET - used_budget;
    if (rem <= 0) return false;
    int t2 = (int)min<long long>(t, rem);
    cout << "RATE " << t2 << endl;
    cout.flush();
    string tok;
    if (!readTokenOrExit(tok)) return false;
    if (tok != "RATES") return false;
    if (!(cin >> w >> d)) exit(0);
    used_budget += t2;
    return true;
}

// Evaluate basic hand category from known cards (max 7). Returns 1..9
int handCategory(const vector<Card>& cards) {
    int cntRank[15] = {0};
    int cntSuit[4] = {0};
    for (auto &c : cards) {
        cntRank[c.rank]++;
        cntSuit[c.suit]++;
    }

    // Flush detection
    int flushSuit = -1;
    for (int s = 0; s < 4; ++s) if (cntSuit[s] >= 5) { flushSuit = s; break; }

    auto hasStraightInRanks = [&](const vector<int>& ranks)->bool{
        bool present[15] = {false};
        for (int r : ranks) present[r] = true;
        // Ace low
        bool ext[15] = {false}; // 1..14
        for (int r=2;r<=14;r++) ext[r]=present[r];
        ext[1] = present[14];
        for (int start = 1; start <= 10; ++start) {
            bool ok = true;
            for (int j = 0; j < 5; ++j) {
                if (!ext[start + j]) { ok = false; break; }
            }
            if (ok) return true;
        }
        return false;
    };

    // Straight flush
    if (flushSuit != -1) {
        vector<int> ranks;
        ranks.reserve(7);
        // collect unique ranks in flush suit
        bool seen[15]={false};
        for (auto &c: cards) if (c.suit == flushSuit) {
            if (!seen[c.rank]) { seen[c.rank]=true; ranks.push_back(c.rank); }
        }
        if (hasStraightInRanks(ranks)) return 9;
    }

    // Four, Full, Trips, Pairs
    int four = 0;
    vector<int> threes, pairs;
    for (int r = 2; r <= 14; ++r) {
        if (cntRank[r] == 4) four = r;
        else if (cntRank[r] == 3) threes.push_back(r);
        else if (cntRank[r] == 2) pairs.push_back(r);
    }
    if (four) return 8;
    if (!threes.empty() && (!pairs.empty() || threes.size() >= 2)) return 7;

    // Flush
    if (flushSuit != -1) return 6;

    // Straight
    {
        vector<int> uniq;
        bool seen[15]={false};
        for (auto &c: cards) if (!seen[c.rank]) { seen[c.rank]=true; uniq.push_back(c.rank); }
        if (hasStraightInRanks(uniq)) return 5;
    }

    // Trips
    if (!threes.empty()) return 4;
    // Two pairs
    if (pairs.size() >= 2) return 3;
    // One pair
    if (pairs.size() == 1) return 2;
    // High card
    return 1;
}

bool flushMadeUsingHole(const vector<Card>& cards, int s1, int s2) {
    int cntSuit[4] = {0};
    for (auto &c: cards) cntSuit[c.suit]++;
    for (int s=0;s<4;s++) {
        if (cntSuit[s] >= 5) {
            if (s1 == s || s2 == s) return true;
        }
    }
    return false;
}

bool flushDrawWithHole(const vector<Card>& cards, int s1, int s2) {
    int cntSuit[4] = {0};
    for (auto &c: cards) cntSuit[c.suit]++;
    for (int s=0;s<4;s++) {
        if (cntSuit[s] == 4) {
            if (s1 == s || s2 == s) return true;
        }
    }
    return false;
}

bool tripsUsingHole(const vector<Card>& cards, int v1, int v2) {
    int cntRank[15] = {0};
    for (auto &c: cards) cntRank[c.rank]++;
    for (int r=2;r<=14;r++) {
        if (cntRank[r] >= 3) {
            if (v1 == r || v2 == r) return true;
        }
    }
    return false;
}

bool twoPairUsingHole(const vector<Card>& cards, const vector<Card>& board, int v1, int v2) {
    int cntRank[15]={0};
    for (auto &c: cards) cntRank[c.rank]++;
    int pairs = 0;
    for (int r=2;r<=14;r++) if (cntRank[r] >= 2) pairs++;
    if (pairs < 2) return false;

    int boardCnt[15]={0};
    for (auto &c: board) boardCnt[c.rank]++;
    if (v1 == v2) return true;
    if (boardCnt[v1] >= 1) return true;
    if (boardCnt[v2] >= 1) return true;
    return false;
}

bool straightUsingHole(const vector<Card>& cards, int v1, int v2) {
    bool present[15]={false};
    for (auto &c: cards) present[c.rank]=true;
    bool ext[15]={false}; // 1..14
    for (int r=2;r<=14;r++) ext[r]=present[r];
    ext[1]=present[14];
    auto inSet = [&](int val, int s)->bool{
        if (s == 1) {
            // A-2-3-4-5
            if (val == 14) return true;
            return (val>=2 && val<=5);
        } else {
            return (val>=s && val<=s+4);
        }
    };
    for (int s=1;s<=10;s++) {
        bool ok=true;
        for (int j=0;j<5;j++) if(!ext[s+j]) { ok=false; break; }
        if (ok) {
            if (inSet(v1, s) || inSet(v2, s)) return true;
        }
    }
    return false;
}

// Preflop decision heuristic
bool preflop_should_raise(int r1, int s1, int r2, int s2) {
    int hi = max(r1, r2);
    int lo = min(r1, r2);
    bool suited = (s1 == s2);
    bool pair = (r1 == r2);

    if (pair) {
        if (hi >= 8) return true; // 88+
        return false;
    }
    // Ace high
    if (hi == 14) {
        if (lo >= 12) return true; // AK, AQ
        if (suited && lo >= 10) return true; // ATs+
        if (suited && lo >= 6) return true;  // A6s+
        return false;
    }
    // King high
    if (hi == 13) {
        if (lo == 12) return true; // KQ
        if (suited && lo >= 11) return true; // KJs+
        return false;
    }
    // Queen high
    if (hi == 12) {
        if (suited && lo >= 11) return true; // QJs
    }
    // Suited connectors 98s+, T9s, JTs
    if (suited && hi - lo == 1 && lo >= 9) return true;

    // Broadways suited like JTs already covered; offsuit broadway pairs?
    if (hi >= 12 && lo >= 11 && hi - lo <= 1) return true; // QJ, KQ (offsuit QJ)

    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Read initial G if present
    string tok;
    if (!(cin >> tok)) return 0;
    if (tok == "-1") return 0;
    // If it's a number, it's G. Otherwise it's token like STATE etc.
    if (!(tok == "STATE" || tok == "RATES" || tok == "OPP" || tok == "RESULT" || tok == "SCORE")) {
        // It's G, ignore
    } else {
        // Put back by handling via logic below
    }
    // Prepare a mechanism to process initial token if it's not G
    string pending = "";
    if (tok == "STATE" || tok == "RATES" || tok == "OPP" || tok == "RESULT" || tok == "SCORE") {
        pending = tok;
    }

    auto process_state = [&](int h, int r, int a, int b, int P, int k) {
        string word;
        cin >> word; // "ALICE"
        int s1,v1,s2,v2;
        cin >> s1 >> v1 >> s2 >> v2;
        cin >> word; // "BOARD"
        vector<Card> board;
        for (int i=0;i<k;i++) {
            int bs, bv; cin >> bs >> bv;
            board.push_back({bs, bv+1});
        }
        // Build cards
        Card c1{ s1, v1+1 }, c2{ s2, v2+1 };
        vector<Card> known = board;
        known.push_back(c1);
        known.push_back(c2);

        auto action_check = [&](){
            cout << "ACTION CHECK" << endl;
            cout.flush();
        };
        auto action_raise = [&](int x){
            if (x < 1) x = 1;
            if (x > a) x = a;
            cout << "ACTION RAISE " << x << endl;
            cout.flush();
        };

        // Decision logic per round
        if (r == 1) {
            // Preflop
            int r1 = c1.rank, r2 = c2.rank;
            bool doRaise = preflop_should_raise(r1, c1.suit, r2, c2.suit);
            if (doRaise && a >= 1) {
                int x = min(a, 5);
                action_raise(x);
            } else {
                action_check();
            }
            return;
        }

        // Postflop categories
        int cat = handCategory(known); // 1..9
        int v1r = c1.rank, v2r = c2.rank;

        if (r == 2) {
            // Flop
            bool raised = false;
            if (cat >= 7) {
                // Full house or better
                int x = min(a, max(1, P));
                action_raise(x); raised = true;
            } else if (!raised && flushMadeUsingHole(known, c1.suit, c2.suit)) {
                int x = min(a, max(1, P/2));
                action_raise(x); raised = true;
            } else if (!raised && cat == 5 && straightUsingHole(known, v1r, v2r)) {
                int x = min(a, max(1, P/2));
                action_raise(x); raised = true;
            } else if (!raised && tripsUsingHole(known, v1r, v2r)) {
                int x = min(a, max(1, P/2));
                action_raise(x); raised = true;
            } else if (!raised && twoPairUsingHole(known, board, v1r, v2r)) {
                int x = min(a, max(1, P/2));
                action_raise(x); raised = true;
            } else if (!raised && flushDrawWithHole(known, c1.suit, c2.suit)) {
                int x = min(a, max(1, P/3));
                action_raise(x); raised = true;
            } else {
                action_check();
            }
            return;
        }

        if (r == 3) {
            // Turn
            bool raised = false;
            if (cat >= 7) {
                int x = min(a, max(1, P));
                action_raise(x); raised = true;
            } else if (!raised && flushMadeUsingHole(known, c1.suit, c2.suit)) {
                int x = min(a, max(1, P));
                action_raise(x); raised = true;
            } else if (!raised && cat == 5 && straightUsingHole(known, v1r, v2r)) {
                int x = min(a, max(1, P/2));
                action_raise(x); raised = true;
            } else if (!raised && tripsUsingHole(known, v1r, v2r)) {
                int x = min(a, max(1, P/2));
                action_raise(x); raised = true;
            } else if (!raised && twoPairUsingHole(known, board, v1r, v2r)) {
                int x = min(a, max(1, P/2));
                action_raise(x); raised = true;
            } else {
                action_check();
            }
            return;
        }

        if (r == 4) {
            // River: use RATE if budget allows
            double w=0.0, d=0.0;
            bool got = false;
            int t_river = 200;
            if (RATE_BUDGET - used_budget >= 20) {
                int t = (int)min<long long>(t_river, RATE_BUDGET - used_budget);
                got = query_rates(t, w, d);
            }
            if (!got) {
                // fallback: raise only with very strong made hands
                bool raised = false;
                if (cat >= 7) { int x = min(a, max(1, P)); action_raise(x); raised = true; }
                else if (!raised && (cat == 6 || cat == 9)) { int x = min(a, max(1, P)); action_raise(x); raised = true; }
                else if (!raised && cat == 5 && straightUsingHole(known, v1r, v2r)) { int x = min(a, max(1, P/2)); action_raise(x); raised = true; }
                else if (!raised && tripsUsingHole(known, v1r, v2r)) { int x = min(a, max(1, P/2)); action_raise(x); raised = true; }
                else action_check();
                return;
            }
            double E = w + 0.5*d;
            if (a <= 0) { action_check(); return; }
            if (E >= 0.90) {
                action_raise(a); // shove for max value
            } else if (E >= 0.75) {
                int x = min(a, max(1, P));
                action_raise(x);
            } else if (E >= 0.62) {
                int x = min(a, max(1, P/2));
                action_raise(x);
            } else {
                action_check();
            }
            return;
        }

        // Fallback
        action_check();
    };

    // Main loop processing tokens
    if (!pending.empty()) {
        // Process pending token first
        if (pending == "STATE") {
            int h,r,a,b,P,k; cin >> h >> r >> a >> b >> P >> k;
            process_state(h,r,a,b,P,k);
        } else if (pending == "RATES") {
            double w,d; cin >> w >> d; // should not generally happen here
        } else if (pending == "OPP") {
            string a2; cin >> a2;
            if (a2 == "CALL") { int x; cin >> x; }
        } else if (pending == "RESULT") {
            int delta; cin >> delta;
        } else if (pending == "SCORE") {
            double W; cin >> W;
        }
        pending.clear();
    }

    while (true) {
        string token;
        if (!(cin >> token)) break;
        if (token == "-1") return 0;
        if (token == "STATE") {
            int h,r,a,b,P,k; cin >> h >> r >> a >> b >> P >> k;
            process_state(h,r,a,b,P,k);
        } else if (token == "RATES") {
            double w,d; cin >> w >> d; // ignore stray
        } else if (token == "OPP") {
            string act; cin >> act;
            if (act == "CALL") { int x; cin >> x; }
            // CHECK/FOLD have no extra ints
        } else if (token == "RESULT") {
            int delta; cin >> delta;
        } else if (token == "SCORE") {
            double W; cin >> W;
            // End of match
            break;
        } else {
            // Possibly the initial G already consumed; ignore others
        }
    }

    return 0;
}