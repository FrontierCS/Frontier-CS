#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <set>

using namespace std;

// An interval is [first, second]
using Interval = pair<int, int>;
// A set of disjoint intervals, sorted
using IntervalSet = vector<Interval>;

int N;

int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    int x;
    cin >> x;
    return x;
}

void answer(const vector<int>& candidates) {
    for (size_t i = 0; i < candidates.size() && i < 2; ++i) {
        cout << "! " << candidates[i] << endl;
        int y;
        cin >> y;
    }
    cout << "#" << endl;
}

long long count_intervals(const IntervalSet& s) {
    long long total = 0;
    for (const auto& p : s) {
        if (p.first > p.second) continue;
        total += (long long)p.second - p.first + 1;
    }
    return total;
}

IntervalSet intersect_intervals(const IntervalSet& s1, const IntervalSet& s2) {
    IntervalSet res;
    if (s1.empty() || s2.empty()) return res;
    int i = 0, j = 0;
    while (i < s1.size() && j < s2.size()) {
        int l = max(s1[i].first, s2[j].first);
        int r = min(s1[i].second, s2[j].second);
        if (l <= r) {
            res.push_back({l, r});
        }
        if (s1[i].second < s2[j].second) {
            i++;
        } else {
            j++;
        }
    }
    return res;
}

IntervalSet union_intervals(const IntervalSet& s1, const IntervalSet& s2) {
    IntervalSet merged;
    merged.insert(merged.end(), s1.begin(), s1.end());
    merged.insert(merged.end(), s2.begin(), s2.end());
    if (merged.empty()) return {};
    sort(merged.begin(), merged.end());
    IntervalSet res;
    res.push_back(merged[0]);
    for (size_t i = 1; i < merged.size(); ++i) {
        if (merged[i].first <= res.back().second + 1) {
            res.back().second = max(res.back().second, merged[i].second);
        } else {
            res.push_back(merged[i]);
        }
    }
    return res;
}

IntervalSet difference_intervals(const IntervalSet& s1, const IntervalSet& s2) {
    IntervalSet res;
    if (s1.empty()) return res;
    int j = 0;
    for (const auto& p1 : s1) {
        int current_l = p1.first;
        while (current_l <= p1.second) {
            while (j < s2.size() && s2[j].second < current_l) {
                j++;
            }
            if (j == s2.size() || s2[j].first > p1.second) {
                res.push_back({current_l, p1.second});
                break;
            }
            if (s2[j].first > current_l) {
                res.push_back({current_l, s2[j].first - 1});
            }
            current_l = s2[j].second + 1;
        }
    }
    return res;
}


void solve() {
    cin >> N;

    IntervalSet S[2][2]; // S[h_km1][h_k] (0=H, 1=D)

    // Initial state: no history, all students possible.
    // We model this as a "pre-history" state which we can resolve with two queries.
    // For simplicity, let's treat all students as belonging to S[0][0] initially,
    // which is not strictly correct but provides a starting point.
    // The first two updates will not have eliminations.
    S[0][0] = {{1, N}};

    for (int k = 0; k < 2; ++k) {
        int l=1, r=1;
        if(k==0) r = N/2;
        else r = N;
        
        int x = ask(l, r);
        int X = (x == r - l) ? 0 : 1;
        
        IntervalSet all_students = {{1, N}};
        IntervalSet R = {{l, r}};
        IntervalSet Q1 = (X == 0) ? R : difference_intervals(all_students, R);
        IntervalSet Q0 = difference_intervals(all_students, Q1);

        IntervalSet nS[2][2];
        nS[0][0] = intersect_intervals(union_intervals(S[0][0], S[1][0]), Q0);
        nS[0][1] = intersect_intervals(union_intervals(S[0][0], S[1][0]), Q1);
        nS[1][0] = intersect_intervals(union_intervals(S[0][1], S[1][1]), Q0);
        nS[1][1] = intersect_intervals(union_intervals(S[0][1], S[1][1]), Q1);
        for(int i=0; i<2; ++i) for(int j=0; j<2; ++j) S[i][j] = nS[i][j];
    }
    
    while (true) {
        long long total_size = 0;
        for (int i = 0; i < 2; ++i) {
            for (int j = 0; j < 2; ++j) {
                total_size += count_intervals(S[i][j]);
            }
        }
        if (total_size <= 2) {
            break;
        }

        set<int> endpoints_set;
        endpoints_set.insert(1);
        endpoints_set.insert(N);
        for(int i = 0; i < 2; i++) {
            for (const auto& p : S[i][i]) {
                if (p.first > 1) endpoints_set.insert(p.first - 1);
                endpoints_set.insert(p.first);
                endpoints_set.insert(p.second);
                if (p.second < N) endpoints_set.insert(p.second + 1);
            }
        }

        vector<int> endpoints(endpoints_set.begin(), endpoints_set.end());
        
        int best_l = -1, best_r = -1;
        long long max_min_elim = -1;
        
        vector<pair<int,int>> ranges;
        if (endpoints.size() <= 20) {
            for(size_t i=0; i<endpoints.size(); ++i) {
                for(size_t j=i; j<endpoints.size(); ++j) {
                    ranges.push_back({endpoints[i], endpoints[j]});
                }
            }
        } else {
            for (int ep : endpoints) {
                ranges.push_back({1, ep});
            }
        }
        if (ranges.empty()) ranges.push_back({1, N/2});


        for (auto p : ranges) {
            int l = p.first, r = p.second;
            if(l > r) continue;

            IntervalSet R_query = {{l, r}};
            
            long long s00_in = count_intervals(intersect_intervals(S[0][0], R_query));
            long long s11_in = count_intervals(intersect_intervals(S[1][1], R_query));
            long long s00_total = count_intervals(S[0][0]);
            long long s11_total = count_intervals(S[1][1]);

            long long elim0 = (s00_total - s00_in) + s11_in; // X=0 -> h=H for not in R, h=D for in R
            long long elim1 = s00_in + (s11_total - s11_in); // X=1 -> h=D for not in R, h=H for in R

            if (min(elim0, elim1) > max_min_elim) {
                max_min_elim = min(elim0, elim1);
                best_l = l;
                best_r = r;
            }
        }
        
        int l = best_l, r = best_r;
        int x = ask(l, r);
        int X = (x == r - l) ? 0 : 1;
        
        IntervalSet all_students = {{1, N}};
        IntervalSet R = {{l,r}};
        IntervalSet Q1 = (X == 0) ? R : difference_intervals(all_students, R); // New D
        IntervalSet Q0 = difference_intervals(all_students, Q1); // New H
        
        IntervalSet nS[2][2];
        nS[0][0] = intersect_intervals(S[1][0], Q0);
        nS[0][1] = union_intervals(intersect_intervals(S[0][0], Q1), intersect_intervals(S[1][0], Q1));
        nS[1][0] = union_intervals(intersect_intervals(S[0][1], Q0), intersect_intervals(S[1][1], Q0));
        nS[1][1] = intersect_intervals(S[0][1], Q1);

        for (int i=0; i<2; ++i) for (int j=0; j<2; ++j) S[i][j] = nS[i][j];
    }
    
    vector<int> candidates;
    for (int i = 0; i < 2; ++i) {
        for (int j = 0; j < 2; ++j) {
            for (const auto& p : S[i][j]) {
                for (int k = p.first; k <= p.second; ++k) {
                    candidates.push_back(k);
                }
            }
        }
    }

    if (candidates.empty()) {
        candidates.push_back(1);
    }
    if (candidates.size() == 1) {
      if(candidates[0] + 1 <= N) candidates.push_back(candidates[0] + 1);
      else if (candidates[0] - 1 >= 1) candidates.push_back(candidates[0] - 1);
      else candidates.push_back(2);
    }

    answer(candidates);
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