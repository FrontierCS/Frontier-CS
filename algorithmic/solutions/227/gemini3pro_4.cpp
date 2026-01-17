#include <iostream>
#include <vector>
#include <algorithm>
#include <iterator>

using namespace std;

// Global variables for problem data
int n;
vector<int> p;

// Function to calculate LIS (or LDS via value inversion) on available elements
// Returns the indices of the subsequence
vector<int> get_subsequence_indices(const vector<bool>& used, bool decreasing) {
    // tails_vals[i] stores the smallest tail of all increasing subsequences of length i+1 found so far.
    // tails_idxs[i] stores the index in p of that tail value.
    vector<int> tails_vals;
    vector<int> tails_idxs;
    vector<int> parent(n, -1);
    
    for (int i = 0; i < n; ++i) {
        if (used[i]) continue;
        
        int val = p[i];
        if (decreasing) val = -val; // Transform problem to LIS
        
        // Find the first element in tails_vals >= val
        auto it = lower_bound(tails_vals.begin(), tails_vals.end(), val);
        int len = distance(tails_vals.begin(), it);
        
        if (it == tails_vals.end()) {
            tails_vals.push_back(val);
            tails_idxs.push_back(i);
        } else {
            *it = val;
            tails_idxs[len] = i;
        }
        
        // If we are extending a sequence of length 'len', the previous element is at tails_idxs[len-1]
        if (len > 0) {
            parent[i] = tails_idxs[len - 1];
        }
    }
    
    // Reconstruct the path
    vector<int> indices;
    if (tails_idxs.empty()) return indices;
    
    int curr = tails_idxs.back();
    while (curr != -1) {
        indices.push_back(curr);
        curr = parent[curr];
    }
    reverse(indices.begin(), indices.end());
    return indices;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    p.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> p[i];
    }

    // We need to extract 2 Increasing and 2 Decreasing subsequences.
    // The order of extraction matters for the greedy approach.
    // We try all distinct permutations of the types order.
    // 0: Increasing, 1: Decreasing
    vector<int> types = {0, 0, 1, 1};
    sort(types.begin(), types.end());
    
    long long best_total_len = -1;
    vector<int> best_owner(n, 3); // Default to d (index 3)
    
    do {
        vector<bool> used(n, false);
        vector<int> current_owner(n, -1);
        long long current_len = 0;
        
        int inc_cnt = 0;
        int dec_cnt = 0;
        
        for (int type : types) {
            int target = -1;
            // Map the occurrence of type to specific output set
            // 1st Inc -> a (0), 2nd Inc -> c (2)
            // 1st Dec -> b (1), 2nd Dec -> d (3)
            if (type == 0) {
                target = (inc_cnt == 0) ? 0 : 2;
                inc_cnt++;
            } else {
                target = (dec_cnt == 0) ? 1 : 3;
                dec_cnt++;
            }
            
            vector<int> indices = get_subsequence_indices(used, type == 1);
            current_len += indices.size();
            
            for (int idx : indices) {
                used[idx] = true;
                current_owner[idx] = target;
            }
        }
        
        if (current_len > best_total_len) {
            best_total_len = current_len;
            for (int i = 0; i < n; ++i) {
                if (current_owner[i] == -1) best_owner[i] = 3;
                else best_owner[i] = current_owner[i];
            }
        }
        
    } while (next_permutation(types.begin(), types.end()));
    
    // Construct the output subsequences based on best_owner
    vector<int> a, b, c, d_seq;
    // Reserve memory to avoid reallocations
    a.reserve(n); b.reserve(n); c.reserve(n); d_seq.reserve(n);
    
    for (int i = 0; i < n; ++i) {
        if (best_owner[i] == 0) a.push_back(p[i]);
        else if (best_owner[i] == 1) b.push_back(p[i]);
        else if (best_owner[i] == 2) c.push_back(p[i]);
        else d_seq.push_back(p[i]);
    }
    
    // Print lengths
    cout << a.size() << " " << b.size() << " " << c.size() << " " << d_seq.size() << "\n";
    
    // Print sequences
    auto print_vec = [](const vector<int>& v) {
        for (int i = 0; i < (int)v.size(); ++i) {
            cout << v[i] << (i == (int)v.size() - 1 ? "" : " ");
        }
        cout << "\n";
    };
    
    print_vec(a);
    print_vec(b);
    print_vec(c);
    print_vec(d_seq);

    return 0;
}