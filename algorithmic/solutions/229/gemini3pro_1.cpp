#include <iostream>
#include <vector>
#include <algorithm>
#include <queue>

using namespace std;

// Function to calculate LIS length for every prefix of the array
vector<int> get_prefix_lis(const vector<long long>& nums) {
    if (nums.empty()) return {};
    vector<int> lis_len;
    lis_len.reserve(nums.size());
    vector<long long> tails;
    for (long long x : nums) {
        auto it = lower_bound(tails.begin(), tails.end(), x);
        if (it == tails.end()) {
            tails.push_back(x);
        } else {
            *it = x;
        }
        lis_len.push_back((int)tails.size());
    }
    return lis_len;
}

// Function to calculate LIS length for every suffix of the array
// Equivalent to LIS of negated values in reversed array (to find "decreasing" sequences)
vector<int> get_suffix_lis(const vector<long long>& nums) {
    if (nums.empty()) return {};
    vector<long long> rev_nums = nums;
    reverse(rev_nums.begin(), rev_nums.end());
    
    // Negate to use LIS logic for LDS
    for (auto& x : rev_nums) x = -x;
    
    vector<int> rev_lis = get_prefix_lis(rev_nums);
    reverse(rev_lis.begin(), rev_lis.end());
    return rev_lis;
}

struct SplitInfo {
    int split_idx; // relative to segment start (0-based index of left part's end)
    int gain;
};

// Represents a segment of the original array
struct Segment {
    int l, r; // 0-based range [l, r] in original array
    int best_split_global_idx;
    int gain;
    
    // Priority queue orders by gain descending
    bool operator<(const Segment& other) const {
        return gain < other.gain;
    }
};

SplitInfo find_best_split(const vector<long long>& nums, int current_lis) {
    int n = (int)nums.size();
    if (n < 2) return {-1, -1};
    
    vector<int> pref = get_prefix_lis(nums);
    vector<int> suff = get_suffix_lis(nums);
    
    int best_gain = -1; 
    int best_idx = -1;
    
    // Check split points
    // Split after i: Left [0...i], Right [i+1...n-1]
    for (int i = 0; i < n - 1; ++i) {
        int potential = pref[i] + suff[i+1];
        int gain = potential - current_lis;
        if (gain > best_gain) {
            best_gain = gain;
            best_idx = i;
        }
    }
    
    return {best_idx, best_gain};
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    long long x;
    if (!(cin >> n >> x)) return 0;

    vector<long long> t(n);
    for (int i = 0; i < n; ++i) {
        cin >> t[i];
    }

    if (n == 0) {
        cout << 0 << "\n";
        for(int i=0; i<10; ++i) cout << "1 1 0\n";
        return 0;
    }

    // Initial LIS calculation
    vector<int> initial_lis_vec = get_prefix_lis(t);
    int initial_lis = initial_lis_vec.empty() ? 0 : initial_lis_vec.back();

    priority_queue<Segment> pq;

    // Initial analysis
    SplitInfo si = find_best_split(t, initial_lis);
    if (si.split_idx != -1 && si.gain > 0) {
        pq.push({0, n - 1, 0 + si.split_idx, si.gain});
    }

    vector<int> cuts;
    int ops = 0;
    const int MAX_OPS = 10;

    // Greedily perform splits
    while (ops < MAX_OPS && !pq.empty()) {
        Segment top = pq.top();
        pq.pop();
        
        // We only proceed with beneficial splits
        if (top.gain <= 0) continue;

        cuts.push_back(top.best_split_global_idx);
        ops++;

        // The split point is 'top.best_split_global_idx' (absolute index)
        // Left segment: top.l to mid
        // Right segment: mid + 1 to top.r
        int mid = top.best_split_global_idx;

        // Process Left Subsegment
        if (mid > top.l) {
            vector<long long> left_sub;
            left_sub.reserve(mid - top.l + 1);
            for (int k = top.l; k <= mid; ++k) left_sub.push_back(t[k]);
            
            int left_lis = get_prefix_lis(left_sub).back();
            SplitInfo si_left = find_best_split(left_sub, left_lis);
            if (si_left.split_idx != -1 && si_left.gain > 0) {
                pq.push({top.l, mid, top.l + si_left.split_idx, si_left.gain});
            }
        }

        // Process Right Subsegment
        if (top.r > mid + 1) {
            vector<long long> right_sub;
            right_sub.reserve(top.r - (mid + 1) + 1);
            for (int k = mid + 1; k <= top.r; ++k) right_sub.push_back(t[k]);
            
            int right_lis = get_prefix_lis(right_sub).back();
            SplitInfo si_right = find_best_split(right_sub, right_lis);
            if (si_right.split_idx != -1 && si_right.gain > 0) {
                pq.push({mid + 1, top.r, mid + 1 + si_right.split_idx, si_right.gain});
            }
        }
    }

    sort(cuts.begin(), cuts.end());

    struct Operation {
        int l, r, d;
    };
    vector<Operation> operations;
    
    // Construct suffix operations
    // Cut at index c means [c+1...n-1] gets +x relative to [0...c]
    // In 1-based indexing: [c+2, n]
    for (int c : cuts) {
        if (c + 2 <= n) {
            operations.push_back({c + 2, n, (int)x});
        }
    }

    // Fill with dummy ops
    while (operations.size() < 10) {
        operations.push_back({1, 1, 0});
    }

    // Calculate Final LIS
    vector<long long> final_t = t;
    for (const auto& op : operations) {
        if (op.d == 0) continue;
        for (int i = op.l - 1; i < op.r; ++i) {
            final_t[i] += op.d;
        }
    }

    int ans = get_prefix_lis(final_t).back();

    cout << ans << "\n";
    for (const auto& op : operations) {
        cout << op.l << " " << op.r << " " << op.d << "\n";
    }

    return 0;
}