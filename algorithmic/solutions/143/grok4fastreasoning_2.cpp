#include <bits/stdc++.h>
using namespace std;

using pii = pair<int, int>;

struct HandRank {
    int type;
    int s_high;
    vector<pii> ties;
    HandRank() : type(0), s_high(0) {}
    bool is_sf_or_s() const { return type == 5 || type == 9; }
};

bool is_better(const HandRank& a, const HandRank& b) {
    if (a.type != b.type) return a.type > b.type;
    if (a.is_sf_or_s()) {
        if (a.s_high != b.s_high) return a.s_high > b.s_high;
        return false;
    }
    const auto& ta = a.ties;
    const auto& tb = b.ties;
    for (size_t i = 0; i < 5; ++i) {
        if (ta[i] != tb[i]) return ta[i] > tb[i];
    }
    return false;
}

HandRank compute_five(const vector<pii>& five) {
    vector<int> values(5), suits(5);
    for (int i = 0; i < 5; ++i) {
        suits[i] = five[i].first;
        values[i] = five[i].second;
    }
    bool is_flush = true;
    int suit0 = suits[0];
    for (int su : suits) if (su != suit0) is_flush = false;
    vector<int> vs = values;
    sort(vs.begin(), vs.end());
    set<int> us(values.begin(), values.end());
    bool is_str = (us.size() == 5) && ((vs[4] - vs[0] == 4) || (us.count(1) && us.count(2) && us.count(3) && us.count(4) && us.count(13)));
    int sh = 0;
    if (is_str) {
        bool wheel = (us.count(13) && us.count(1) && us.count(2) && us.count(3) && us.count(4));
        sh = wheel ? 4 : vs[4];
    }
    int cnt[14] = {0};
    for (int v : values) ++cnt[v];
    int num_pairs = 0, num_threes = 0, num_fours = 0;
    for (int i = 1; i <= 13; ++i) {
        if (cnt[i] == 4) ++num_fours;
        else if (cnt[i] == 3) ++num_threes;
        else if (cnt[i] == 2) ++num_pairs;
    }
    int ttyp = 1;
    if (is_flush && is_str) ttyp = 9;
    else if (num_fours > 0) ttyp = 8;
    else if (num_threes > 0 && num_pairs > 0) ttyp = 7;
    else if (is_flush) ttyp = 6;
    else if (is_str) ttyp = 5;
    else if (num_threes > 0) ttyp = 4;
    else if (num_pairs == 2) ttyp = 3;
    else if (num_pairs == 1) ttyp = 2;
    HandRank hr;
    hr.type = ttyp;
    hr.s_high = sh;
    if (!hr.is_sf_or_s()) {
        vector<pii> tt(5);
        for (int i = 0; i < 5; ++i) {
            tt[i] = {cnt[values[i]], values[i]};
        }
        sort(tt.rbegin(), tt.rend());
        hr.ties = tt;
    }
    return hr;
}

HandRank best_rank(const vector<pii>& seven) {
    HandRank best;
    int n = 7;
    for (int mask = 0; mask < (1 << n); ++mask) {
        if (__builtin_popcount(mask) != 5) continue;
        vector<pii> five;
        for (int i = 0; i < n; ++i) {
            if (mask & (1 << i)) five.push_back(seven[i]);
        }
        HandRank cur = compute_five(five);
        if (is_better(cur, best)) best = cur;
    }
    return best;
}

string next_token() {
    string s;
    cin >> s;
    if (s == "-1") exit(0);
    return s;
}

int read_int() {
    return stoi(next_token());
}

double read_double() {
    return stod(next_token());
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    read_int(); // G
    random_device rd;
    mt19937 rng(rd());
    vector<pii> my_cards(2), current_board;
    auto get_id = [](int cs, int vs) { return cs * 13 + (vs - 1); };
    while (true) {
        string tok = next_token();
        if (tok == "SCORE") {
            read_double();
            return 0;
        }
        // assume STATE
        int h = read_int();
        int r = read_int();
        int a = read_int();
        int b = read_int();
        int P = read_int();
        int k = read_int();
        next_token(); // ALICE
        int c1 = read_int(), v1 = read_int(), c2 = read_int(), v2 = read_int();
        my_cards = {{c1, v1}, {c2, v2}};
        next_token(); // BOARD
        current_board.resize(k);
        for (int i = 0; i < k; ++i) {
            int cs = read_int(), vs = read_int();
            current_board[i] = {cs, vs};
        }
        // compute
        vector<bool> used(52, false);
        for (auto& cd : my_cards) used[get_id(cd.first, cd.second)] = true;
        for (auto& cd : current_board) used[get_id(cd.first, cd.second)] = true;
        vector<int> avail;
        for (int i = 0; i < 52; ++i) if (!used[i]) avail.push_back(i);
        int m = 5 - k;
        int outer_t, inner_t;
        if (r == 1) { outer_t = 20; inner_t = 10; }
        else if (r == 2) { outer_t = 25; inner_t = 10; }
        else if (r == 3) { outer_t = 30; inner_t = 10; }
        else { outer_t = 40; inner_t = 20; }
        vector<double> my_ress(outer_t, 0.0);
        vector<double> her_eqs(outer_t, 0.0);
        for (int s = 0; s < outer_t; ++s) {
            vector<int> temp_avail = avail;
            shuffle(temp_avail.begin(), temp_avail.end(), rng);
            vector<pii> bob_c(2);
            for (int j = 0; j < 2; ++j) {
                int id = temp_avail[j];
                int ss = id / 13;
                int vv = (id % 13) + 1;
                bob_c[j] = {ss, vv};
            }
            vector<pii> comm(m);
            for (int j = 0; j < m; ++j) {
                int id = temp_avail[2 + j];
                int ss = id / 13;
                int vv = (id % 13) + 1;
                comm[j] = {ss, vv};
            }
            vector<pii> full_board = current_board;
            full_board.insert(full_board.end(), comm.begin(), comm.end());
            vector<pii> my7 = my_cards;
            my7.insert(my7.end(), full_board.begin(), full_board.end());
            vector<pii> bob7 = bob_c;
            bob7.insert(bob7.end(), full_board.begin(), full_board.end());
            HandRank mr = best_rank(my7);
            HandRank br = best_rank(bob7);
            bool iwin = is_better(mr, br);
            bool bwin = is_better(br, mr);
            double mres = iwin ? 1.0 : (bwin ? 0.0 : 0.5);
            my_ress[s] = mres;
            // her_eq
            vector<bool> h_used(52, false);
            for (auto cd : current_board) h_used[get_id(cd.first, cd.second)] = true;
            for (auto cd : bob_c) h_used[get_id(cd.first, cd.second)] = true;
            vector<int> h_avail;
            for (int i = 0; i < 52; ++i) if (!h_used[i]) h_avail.push_back(i);
            double h_prof = 0.0;
            for (int inn = 0; inn < inner_t; ++inn) {
                vector<int> sim_temp = h_avail;
                shuffle(sim_temp.begin(), sim_temp.end(), rng);
                vector<pii> sim_my(2);
                for (int j = 0; j < 2; ++j) {
                    int id = sim_temp[j];
                    int ss = id / 13;
                    int vv = (id % 13) + 1;
                    sim_my[j] = {ss, vv};
                }
                vector<pii> sim_c(m);
                for (int j = 0; j < m; ++j) {
                    int id = sim_temp[2 + j];
                    int ss = id / 13;
                    int vv = (id % 13) + 1;
                    sim_c[j] = {ss, vv};
                }
                vector<pii> fsim_board = current_board;
                fsim_board.insert(fsim_board.end(), sim_c.begin(), sim_c.end());
                vector<pii> msim7 = sim_my;
                msim7.insert(msim7.end(), fsim_board.begin(), fsim_board.end());
                vector<pii> bsim7 = bob_c;
                bsim7.insert(bsim7.end(), fsim_board.begin(), fsim_board.end());
                HandRank msr = best_rank(msim7);
                HandRank bsr = best_rank(bsim7);
                bool hwin = is_better(bsr, msr);
                bool mwin = is_better(msr, bsr);
                double rres = hwin ? 1.0 : (mwin ? 0.0 : 0.5);
                h_prof += rres;
            }
            her_eqs[s] = h_prof / inner_t;
        }
        double avg_my_eq = 0.0;
        for (double e : my_ress) avg_my_eq += e;
        avg_my_eq /= outer_t;
        double ev_check = (double)a - 100.0 + (double)P * avg_my_eq;
        double best_ev = ev_check;
        int bestx = 0;
        for (int x = 1; x <= a; ++x) {
            double th = (double)x / (P + 2.0 * x);
            double evx = 0.0;
            for (int s = 0; s < outer_t; ++s) {
                bool cl = her_eqs[s] > th;
                double prf;
                if (!cl) {
                    prf = (double)a + P - 100.0;
                } else {
                    double npot = P + 2.0 * x;
                    double nstack = a - (double)x + npot * my_ress[s];
                    prf = nstack - 100.0;
                }
                evx += prf;
            }
            evx /= outer_t;
            if (evx > best_ev + 1e-6) {
                best_ev = evx;
                bestx = x;
            }
        }
        bool do_raise = (bestx > 0);
        if (do_raise) {
            cout << "ACTION RAISE " << bestx << endl;
        } else {
            cout << "ACTION CHECK" << endl;
        }
        // response
        next_token(); // OPP
        string action_opp = next_token();
        if (action_opp == "CHECK") {
            if (r == 4) {
                next_token(); // RESULT
                read_int(); // delta
            }
        } else if (action_opp == "FOLD") {
            next_token(); // RESULT
            read_int(); // delta
        } else if (action_opp == "CALL") {
            read_int(); // x
            if (r == 4) {
                next_token(); // RESULT
                read_int(); // delta
            }
        }
    }
    return 0;
}