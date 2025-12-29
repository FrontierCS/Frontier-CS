#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <tuple>
#include <set>

using namespace std;

// State: {L, R, h_count, d_count}
using Scenario = tuple<int, int, int, int>;

int do_query(int l, int r) {
    cout << "? " << l << " " << r << endl;
    int x;
    cin >> x;
    return x;
}

void do_answer(const vector<int>& candidates) {
    if (candidates.empty()) {
        cout << "! " << 1 << endl;
        int y;
        cin >> y;
        if (y == 0) {
            cout << "! " << 2 << endl;
            cin >> y;
        }
        return;
    }
    for (size_t i = 0; i < min((size_t)2, candidates.size()); ++i) {
        cout << "! " << candidates[i] << endl;
        int y;
        cin >> y;
        if (y == 1) return;
    }
}

// Given a query (qL,qR), its response qX, and a scenario s,
// return a vector of possible resulting scenarios. A scenario may be consistent
// with an honest response, a dishonest one, both, or neither.
vector<Scenario> get_next_scenarios(const Scenario& s, int qL, int qR, int qX) {
    vector<Scenario> next;
    auto [sL, sR, h, d] = s;

    // This simplified logic works if the scenario range is fully contained in or disjoint from the query range
    if (!((sR < qL || sL > qR) || (sL >= qL && sR <= qR))) {
        // This case should not be hit by the implemented strategy
        return {};
    }

    bool A_is_in_query_range = (sL >= qL && sR <= qR);
    int query_len = qR - qL + 1;

    // Hypothesis: response was honest
    if (h < 2) {
        int honest_response = A_is_in_query_range ? (query_len - 1) : query_len;
        if (qX == honest_response) {
            next.emplace_back(sL, sR, h + 1, 0);
        }
    }

    // Hypothesis: response was dishonest
    if (d < 2) {
        int dishonest_response = A_is_in_query_range ? query_len : (query_len - 1);
        if (qX == dishonest_response) {
            next.emplace_back(sL, sR, 0, d + 1);
        }
    }
    return next;
}

void solve() {
    int n;
    cin >> n;

    vector<Scenario> scenarios;
    scenarios.emplace_back(1, n, 0, 0);

    while (true) {
        long long total_size = 0;
        for (const auto& s : scenarios) {
            total_size += (get<1>(s) - get<0>(s) + 1);
        }

        if (total_size <= 2) {
            vector<int> candidates;
            for (const auto& s : scenarios) {
                for (int i = get<0>(s); i <= get<1>(s); ++i) {
                    candidates.push_back(i);
                }
            }
            do_answer(candidates);
            break;
        }

        if (scenarios.size() == 1) {
            auto [L, R, h, d] = scenarios[0];
            if (h == 2 || d == 2) {
                // Forced move, one query halves the range
                int M = L + (R - L) / 2;
                int q_len = M - L + 1;
                int x = do_query(L, M);

                bool must_be_honest = (d == 2);
                int newL, newR;

                if (must_be_honest) {
                    if (x == q_len) { newL = M + 1; newR = R; } 
                    else { newL = L; newR = M; }
                } else { // must_be_dishonest
                    if (x == q_len) { newL = L; newR = M; }
                    else { newL = M + 1; newR = R; }
                }

                int new_h = must_be_honest ? h + 1 : 0;
                int new_d = must_be_honest ? 0 : d + 1;
                scenarios[0] = {newL, newR, new_h, new_d};

            } else {
                // Unforced move, use 2 queries to split into up to 3 scenarios
                int len = R - L + 1;
                int s1_len = len / 3;
                int s2_len = (len - s1_len) / 2;
                
                int L1 = L, R1 = L + s1_len - 1;
                int L2 = R1 + 1, R2 = L2 + s2_len - 1;
                int L3 = R2 + 1, R3 = R;

                int x1 = (s1_len > 0) ? do_query(L1, R1) : -1;
                int x2 = (s2_len > 0) ? do_query(L2, R2) : -1;
                
                vector<Scenario> next_scenarios;
                auto add_if_valid = [&](int pL, int pR, int new_h, int new_d){
                    if(pL <= pR) next_scenarios.emplace_back(pL, pR, new_h, new_d);
                };

                if (x1 == s1_len && x2 == s2_len) { // HH->P3, HD->P2, DH->P1
                    if (h == 0) add_if_valid(L3, R3, 2, 0);
                    if (h < 2)  add_if_valid(L2, R2, 0, 1);
                    if (d < 2)  add_if_valid(L1, R1, 1, 0);
                } else if (x1 == s1_len && x2 == s2_len - 1) { // HH->P1, DH->P3, DD->P2
                    if (h == 0) add_if_valid(L1, R1, 2, 0);
                    if (d < 2)  add_if_valid(L3, R3, 1, 0);
                    if (d == 0) add_if_valid(L2, R2, 0, 2);
                } else if (x1 == s1_len - 1 && x2 == s2_len) { // HH->P2, HD->P3, DD->P1
                    if (h == 0) add_if_valid(L2, R2, 2, 0);
                    if (h < 2)  add_if_valid(L3, R3, 0, 1);
                    if (d == 0) add_if_valid(L1, R1, 0, 2);
                } else if (x1 == s1_len - 1 && x2 == s2_len - 1) { // HD->P1, DH->P2, DD->P3
                    if (h < 2)  add_if_valid(L1, R1, 0, 1);
                    if (d < 2)  add_if_valid(L2, R2, 1, 0);
                    if (d == 0) add_if_valid(L3, R3, 0, 2);
                }
                scenarios = next_scenarios;
            }
        } else { // scenarios.size() > 1
            // Use one query on a forced range to prune scenarios
            int forced_idx = -1;
            for (size_t i = 0; i < scenarios.size(); ++i) {
                if (get<2>(scenarios[i]) == 2 || get<3>(scenarios[i]) == 2) {
                    forced_idx = i;
                    break;
                }
            }
            // A 2-query split from a non-forced state always creates at least one forced state (h=2 or d=2) if possible.
            // If not possible (h=1 or d=1), it creates non-forced states. In this case, just pick any to query.
            if (forced_idx == -1) forced_idx = 0;
            
            auto [qL, qR, qh, qd] = scenarios[forced_idx];
            int x = do_query(qL, qR);
            
            vector<Scenario> next_scenarios;
            for (const auto& s : scenarios) {
                auto res = get_next_scenarios(s, qL, qR, x);
                next_scenarios.insert(next_scenarios.end(), res.begin(), res.end());
            }
            scenarios = next_scenarios;
        }
    }
    cout << "#" << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}