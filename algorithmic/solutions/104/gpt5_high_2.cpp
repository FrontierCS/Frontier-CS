#include <bits/stdc++.h>
using namespace std;

struct Interval {
    int l, r; // inclusive
    bool operator<(const Interval& other) const {
        if (l != other.l) return l < other.l;
        return r < other.r;
    }
};

static void merge_intervals(vector<Interval>& v) {
    if (v.empty()) return;
    sort(v.begin(), v.end());
    vector<Interval> res;
    Interval cur = v[0];
    for (size_t i = 1; i < v.size(); ++i) {
        if (v[i].l <= cur.r + 1) {
            cur.r = max(cur.r, v[i].r);
        } else {
            if (cur.l <= cur.r) res.push_back(cur);
            cur = v[i];
        }
    }
    if (cur.l <= cur.r) res.push_back(cur);
    v.swap(res);
}

static int intervals_size(const vector<Interval>& v) {
    long long s = 0;
    for (auto &in : v) {
        if (in.r >= in.l) s += (in.r - in.l + 1);
    }
    if (s > INT_MAX) s = INT_MAX; // just to be safe
    return (int)s;
}

static vector<Interval> union_of_states(const vector<vector<Interval>>& states, const vector<int>& ids) {
    vector<Interval> all;
    for (int id : ids) {
        for (auto &in : states[id]) {
            if (in.l <= in.r) all.push_back(in);
        }
    }
    merge_intervals(all);
    return all;
}

static vector<Interval> union_all_states(const vector<vector<Interval>>& states) {
    vector<Interval> all;
    for (int id = 0; id < 4; ++id) {
        for (auto &in : states[id]) {
            if (in.l <= in.r) all.push_back(in);
        }
    }
    merge_intervals(all);
    return all;
}

static vector<Interval> intersect_leq(const vector<Interval>& vec, int m) {
    vector<Interval> res;
    for (auto &in : vec) {
        int l = in.l, r = in.r;
        if (l <= m) {
            res.push_back({l, min(r, m)});
        }
    }
    merge_intervals(res);
    return res;
}

static vector<Interval> intersect_gt(const vector<Interval>& vec, int m) {
    vector<Interval> res;
    for (auto &in : vec) {
        int l = in.l, r = in.r;
        if (r > m) {
            res.push_back({max(l, m + 1), r});
        }
    }
    merge_intervals(res);
    return res;
}

static int pick_median_cut(const vector<Interval>& uni) {
    // pick m so that count of s <= m equals floor(total/2)
    int total = intervals_size(uni);
    int k = total / 2; // floor
    // k >= 1 if total >= 2
    int c = 0;
    for (auto &in : uni) {
        int len = in.r - in.l + 1;
        if (c + len >= k && k > 0) {
            int offset = k - c - 1; // zero-based within this interval
            return in.l + offset;
        }
        c += len;
    }
    // if k == 0, choose m as (smallest value - 1) but ensure >=1
    if (!uni.empty()) {
        int m = uni.front().l - 1;
        if (m < 1) m = 1; // ensure valid
        return m;
    }
    return 1; // fallback
}

static int allowed_queries(int n) {
    // 2 * ceil(log_{1.116} n)
    long double base = 1.116L;
    long double acc = 1.0L;
    int k = 0;
    while (acc + 1e-18L < (long double)n) {
        acc *= base;
        k++;
        if (k > 10000) break; // safety
    }
    return 2 * k;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) {
        return 0;
    }
    while (t--) {
        int n;
        cin >> n;
        
        // States: id 0: lastD=0, runLen=1
        //         id 1: lastD=0, runLen=2
        //         id 2: lastD=1, runLen=1
        //         id 3: lastD=1, runLen=2
        vector<vector<Interval>> states(4);
        
        bool fresh = true;
        vector<Interval> fresh_base; // only used if fresh == true
        fresh_base.push_back({1, n});
        
        int qlim = allowed_queries(n);
        int used = 0;
        
        auto current_union_all = [&]() -> vector<Interval> {
            if (fresh) {
                vector<Interval> all = fresh_base;
                for (int id = 0; id < 4; ++id) {
                    for (auto &in : states[id]) all.push_back(in);
                }
                merge_intervals(all);
                return all;
            } else {
                return union_all_states(states);
            }
        };
        
        auto total_candidates = [&]() -> int {
            auto uni = current_union_all();
            return intervals_size(uni);
        };
        
        while (true) {
            int left = total_candidates();
            if (left <= 2) break;
            if (used >= qlim) break;
            
            // Build union over runLen=2 states
            vector<Interval> uni2;
            {
                vector<Interval> temp;
                if (!fresh) {
                    for (auto &in : states[1]) temp.push_back(in);
                    for (auto &in : states[3]) temp.push_back(in);
                }
                merge_intervals(temp);
                uni2 = temp;
            }
            vector<Interval> uni;
            if (!uni2.empty()) {
                uni = uni2;
            } else {
                // fall back to union across all
                uni = current_union_all();
            }
            int total = intervals_size(uni);
            if (total <= 2) break;
            int m = pick_median_cut(uni);
            if (m < 1) m = 1;
            if (m > n) m = n;
            // ensure 1 <= m <= n
            cout << "? " << 1 << " " << m << "\n";
            cout.flush();
            int x;
            if (!(cin >> x)) return 0;
            int d = m - x; // 0 or 1
            
            // update states
            vector<vector<Interval>> nextStates(4);
            // handle fresh base
            if (fresh) {
                for (int nextD = 0; nextD <= 1; ++nextD) {
                    int v = d ^ nextD;
                    vector<Interval> inter;
                    if (v == 1) {
                        inter = intersect_leq(fresh_base, m);
                    } else {
                        inter = intersect_gt(fresh_base, m);
                    }
                    if (!inter.empty()) {
                        int id = (nextD == 0 ? 0 : 2); // runLen=1
                        for (auto &in : inter) nextStates[id].push_back(in);
                    }
                }
                fresh = false;
            }
            // process existing states
            auto process_state = [&](int lastD, int runLen, const vector<Interval>& vec) {
                if (vec.empty()) return;
                if (runLen == 2) {
                    int nextD = 1 - lastD;
                    int v = d ^ nextD;
                    vector<Interval> inter;
                    if (v == 1) inter = intersect_leq(vec, m);
                    else inter = intersect_gt(vec, m);
                    if (!inter.empty()) {
                        int id = (nextD == 0 ? 0 : 2); // runLen becomes 1
                        for (auto &in : inter) nextStates[id].push_back(in);
                    }
                } else { // runLen == 1
                    // nextD == lastD -> runLen=2
                    {
                        int nextD = lastD;
                        int v = d ^ nextD;
                        vector<Interval> inter;
                        if (v == 1) inter = intersect_leq(vec, m);
                        else inter = intersect_gt(vec, m);
                        if (!inter.empty()) {
                            int id = (nextD == 0 ? 1 : 3); // runLen=2
                            for (auto &in : inter) nextStates[id].push_back(in);
                        }
                    }
                    // nextD != lastD -> runLen=1
                    {
                        int nextD = 1 - lastD;
                        int v = d ^ nextD;
                        vector<Interval> inter;
                        if (v == 1) inter = intersect_leq(vec, m);
                        else inter = intersect_gt(vec, m);
                        if (!inter.empty()) {
                            int id = (nextD == 0 ? 0 : 2); // runLen=1
                            for (auto &in : inter) nextStates[id].push_back(in);
                        }
                    }
                }
            };
            process_state(0, 1, states[0]);
            process_state(0, 2, states[1]);
            process_state(1, 1, states[2]);
            process_state(1, 2, states[3]);
            
            // merge intervals in each next state
            for (int id = 0; id < 4; ++id) merge_intervals(nextStates[id]);
            states.swap(nextStates);
            used++;
        }
        
        // Prepare candidates (up to 2)
        vector<Interval> uni = current_union_all();
        merge_intervals(uni);
        vector<int> cand;
        for (auto &in : uni) {
            for (int v = in.l; v <= in.r; ++v) {
                cand.push_back(v);
                if ((int)cand.size() >= 2) break;
            }
            if ((int)cand.size() >= 2) break;
        }
        if (cand.empty()) {
            // Fallback: choose 1 and 2
            if (n >= 1) cand.push_back(1);
            if (n >= 2) cand.push_back(2);
        } else if ((int)cand.size() == 1) {
            // If only one candidate, keep as is
        }
        
        // Make up to 2 guesses
        bool done = false;
        for (int i = 0; i < (int)cand.size() && i < 2; ++i) {
            cout << "! " << cand[i] << "\n";
            cout.flush();
            int y;
            if (!(cin >> y)) return 0;
            if (y == 1) {
                done = true;
                break;
            }
        }
        // If we made fewer than 2 guesses and not done, guess another arbitrary different one
        if (!done && (int)cand.size() < 2) {
            int other = 1;
            if (!cand.empty() && other == cand[0]) other = (cand[0] == 1 ? 2 : 1);
            cout << "! " << other << "\n";
            cout.flush();
            int y;
            if (!(cin >> y)) return 0;
            (void)y;
        }
        cout << "#\n";
        cout.flush();
    }
    return 0;
}