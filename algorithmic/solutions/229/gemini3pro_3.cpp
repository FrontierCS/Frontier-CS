#include <iostream>
#include <vector>
#include <algorithm>
#include <tuple>

using namespace std;

// Function to compute LIS length of a vector
int get_lis_len(const vector<long long>& v) {
    if (v.empty()) return 0;
    vector<long long> tails;
    for (long long x : v) {
        auto it = lower_bound(tails.begin(), tails.end(), x);
        if (it == tails.end()) {
            tails.push_back(x);
        } else {
            *it = x;
        }
    }
    return tails.size();
}

struct Segment {
    int l, r; // 0-based range [l, r)
    int split_point; // best split point absolute index
    int best_gain; // gain if split
    int lis_len; // current LIS length
};

const int INF = 1e9;
int n;
long long x_limit;
vector<long long> t;

// Helper to calculate best split for range [L, R)
// Returns {gain, split_index, current_lis}
// split_index is k such that left is [L, k), right is [k, R)
tuple<int, int, int> evaluate_segment(int L, int R) {
    if (R - L < 2) {
        // Cannot split into 2 non-empty segments
        vector<long long> sub;
        for(int i=L; i<R; ++i) sub.push_back(t[i]);
        return {-INF, -1, get_lis_len(sub)};
    }

    int len = R - L;
    
    // Forward LIS lengths
    // fwd[i] stores LIS length of t[L ... L+i]
    vector<int> fwd(len);
    vector<long long> tails;
    tails.reserve(len);
    for (int i = 0; i < len; ++i) {
        long long val = t[L + i];
        auto it = lower_bound(tails.begin(), tails.end(), val);
        if (it == tails.end()) tails.push_back(val);
        else *it = val;
        fwd[i] = tails.size();
    }
    int total_lis = tails.size();

    // Backward LIS lengths
    // bwd[i] stores LIS length of t[L+i ... R-1]
    // Calculated by iterating backwards and using negative values (equivalent to LDS)
    vector<int> bwd(len);
    tails.clear();
    for (int i = len - 1; i >= 0; --i) {
        long long val = -t[L + i]; 
        auto it = lower_bound(tails.begin(), tails.end(), val);
        if (it == tails.end()) tails.push_back(val);
        else *it = val;
        bwd[i] = tails.size();
    }

    // Find max gain
    int max_sum = -1;
    int best_k = -1;

    // Split at k means left: [0, k-1] (indices L to L+k-1), right: [k, len-1] (indices L+k to R-1)
    // k ranges from 1 to len-1
    for (int k = 1; k < len; ++k) {
        int sum_lis = fwd[k-1] + bwd[k];
        if (sum_lis > max_sum) {
            max_sum = sum_lis;
            best_k = L + k;
        }
    }

    return {max_sum - total_lis, best_k, total_lis};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> x_limit)) return 0;
    t.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> t[i];
    }

    // List of active segments
    vector<Segment> segments;
    
    // Initial segment
    auto init_eval = evaluate_segment(0, n);
    segments.push_back({0, n, get<1>(init_eval), get<0>(init_eval), get<2>(init_eval)});

    int ops = 10;
    while (ops > 0) {
        // Find best segment to split
        int best_seg_idx = -1;
        int max_gain = -1e9; 
        
        for (int i = 0; i < segments.size(); ++i) {
            if (segments[i].best_gain > -INF) {
                if (segments[i].best_gain > max_gain) {
                    max_gain = segments[i].best_gain;
                    best_seg_idx = i;
                }
            }
        }

        if (best_seg_idx == -1) break; 

        // Perform split
        Segment to_split = segments[best_seg_idx];
        int k = to_split.split_point;
        
        segments.erase(segments.begin() + best_seg_idx);
        
        auto res1 = evaluate_segment(to_split.l, k);
        segments.push_back({to_split.l, k, get<1>(res1), get<0>(res1), get<2>(res1)});
        
        auto res2 = evaluate_segment(k, to_split.r);
        segments.push_back({k, to_split.r, get<1>(res2), get<0>(res2), get<2>(res2)});
        
        ops--;
    }

    // Collect split points
    vector<int> split_points;
    for (const auto& seg : segments) {
        if (seg.l != 0) {
            split_points.push_back(seg.l);
        }
    }
    
    sort(split_points.begin(), split_points.end());
    
    struct Op {
        int l, r, d;
    };
    vector<Op> final_ops;
    for (int p : split_points) {
        final_ops.push_back({p + 1, n, (int)x_limit}); 
    }
    
    // Fill remaining ops with dummies
    while (final_ops.size() < 10) {
        final_ops.push_back({1, 1, 0});
    }

    // Apply ops to a temporary array to compute real LIS
    vector<long long> t_mod = t;
    for (const auto& op : final_ops) {
        for (int i = op.l - 1; i < op.r; ++i) {
            t_mod[i] += op.d;
        }
    }
    
    int final_len = get_lis_len(t_mod);
    
    cout << final_len << "\n";
    for (const auto& op : final_ops) {
        cout << op.l << " " << op.r << " " << op.d << "\n";
    }

    return 0;
}