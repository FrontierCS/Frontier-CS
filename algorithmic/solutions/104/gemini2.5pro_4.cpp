#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <map>

using namespace std;

// Function to ask a query
int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    int x;
    cin >> x;
    return x;
}

// Function to make a guess
bool guess(int a) {
    cout << "! " << a << endl;
    int y;
    cin >> y;
    return y == 1;
}

// Function to signal end of test case
void end_case() {
    cout << "#" << endl;
}

struct Range {
    int l, r;
    bool operator<(const Range& other) const {
        if (l != other.l) return l < other.l;
        return r < other.r;
    }
};

// Represents a hypothesis: a set of candidate ranges for a given honesty streak state
struct Hypothesis {
    vector<Range> ranges;
    int h_streak, d_streak;

    long long total_size() const {
        long long sz = 0;
        for (const auto& range : ranges) {
            sz += range.r - range.l + 1;
        }
        return sz;
    }
};

void solve() {
    int n;
    cin >> n;

    vector<Hypothesis> hypos;
    hypos.push_back({{{1, n}}, 0, 0});

    while (true) {
        vector<int> all_candidates;
        for (const auto& h : hypos) {
            for (const auto& range : h.ranges) {
                for (int i = range.l; i <= range.r; ++i) {
                    all_candidates.push_back(i);
                }
            }
        }
        sort(all_candidates.begin(), all_candidates.end());
        all_candidates.erase(unique(all_candidates.begin(), all_candidates.end()), all_candidates.end());

        if (all_candidates.size() <= 2) {
            bool found = false;
            for (int cand : all_candidates) {
                if (guess(cand)) {
                    found = true;
                    break;
                }
            }
            // If the first guess was wrong, the second must be right (if exists)
            if (!found && all_candidates.size() == 2) {
                 // The problem guarantees one is absent. We've tried one. If it failed,
                 // the other must be the one. We don't need to guess again, just move on.
                 // But to be safe and handle all cases, we can make the second guess.
                 int second_cand = (all_candidates[0] == all_candidates[0]) ? all_candidates[1] : all_candidates[0]; //This is silly, just get the other one.
                 bool first_guessed = true;
                 for (int cand: all_candidates) {
                     if (first_guessed) {
                         first_guessed = false;
                         continue;
                     }
                     if (guess(cand)) break;
                 }
            }
            break;
        }
        
        int l_query, r_query;
        int median_idx = all_candidates.size() / 2;
        l_query = all_candidates[0];
        r_query = all_candidates[median_idx-1];
        if (l_query > r_query) r_query = l_query;
        
        int response = ask(l_query, r_query);
        int len = r_query - l_query + 1;

        vector<Hypothesis> next_hypos;
        for (const auto& h : hypos) {
            // Honest case
            if (h.h_streak < 2) {
                // Absent outside query range: response should be len
                if (response == len) {
                    vector<Range> next_ranges;
                    for (const auto& range : h.ranges) {
                        if (range.r < l_query || range.l > r_query) {
                            next_ranges.push_back(range);
                        } else {
                            if (range.l < l_query) next_ranges.push_back({range.l, l_query - 1});
                            if (range.r > r_query) next_ranges.push_back({r_query + 1, range.r});
                        }
                    }
                    if (!next_ranges.empty()) next_hypos.push_back({next_ranges, h.h_streak + 1, 0});
                }
                // Absent inside query range: response should be len - 1
                if (response == len - 1) {
                    vector<Range> next_ranges;
                    for (const auto& range : h.ranges) {
                        int cur_l = max(range.l, l_query);
                        int cur_r = min(range.r, r_query);
                        if (cur_l <= cur_r) next_ranges.push_back({cur_l, cur_r});
                    }
                    if (!next_ranges.empty()) next_hypos.push_back({next_ranges, h.h_streak + 1, 0});
                }
            }

            // Dishonest case
            if (h.d_streak < 2) {
                // Absent outside query range (lied): response is len - 1
                if (response == len - 1) {
                    vector<Range> next_ranges;
                    for (const auto& range : h.ranges) {
                         if (range.r < l_query || range.l > r_query) {
                            next_ranges.push_back(range);
                        } else {
                            if (range.l < l_query) next_ranges.push_back({range.l, l_query - 1});
                            if (range.r > r_query) next_ranges.push_back({r_query + 1, range.r});
                        }
                    }
                    if (!next_ranges.empty()) next_hypos.push_back({next_ranges, 0, h.d_streak + 1});
                }
                // Absent inside query range (lied): response is len
                if (response == len) {
                     vector<Range> next_ranges;
                    for (const auto& range : h.ranges) {
                        int cur_l = max(range.l, l_query);
                        int cur_r = min(range.r, r_query);
                        if (cur_l <= cur_r) next_ranges.push_back({cur_l, cur_r});
                    }
                    if (!next_ranges.empty()) next_hypos.push_back({next_ranges, 0, h.d_streak + 1});
                }
            }
        }
        hypos = next_hypos;

        // Merge hypotheses with same state
        map<pair<int, int>, vector<Range>> merged_ranges;
        for(const auto& h : hypos) {
            merged_ranges[{h.h_streak, h.d_streak}].insert(
                merged_ranges[{h.h_streak, h.d_streak}].end(),
                h.ranges.begin(), h.ranges.end()
            );
        }

        hypos.clear();
        for(auto const& [state, ranges_vec] : merged_ranges) {
            vector<Range> current_ranges = ranges_vec;
            sort(current_ranges.begin(), current_ranges.end());
            vector<Range> simplified_ranges;
            if(!current_ranges.empty()) {
                simplified_ranges.push_back(current_ranges[0]);
                for(size_t i = 1; i < current_ranges.size(); ++i) {
                    if(current_ranges[i].l <= simplified_ranges.back().r + 1) {
                        simplified_ranges.back().r = max(simplified_ranges.back().r, current_ranges[i].r);
                    } else {
                        simplified_ranges.push_back(current_ranges[i]);
                    }
                }
            }
            if(!simplified_ranges.empty()) {
                 hypos.push_back({simplified_ranges, state.first, state.second});
            }
        }
    }
    end_case();
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