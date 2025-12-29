/**
 * Interactive RBS
 * Solution Overview:
 * 1. Find a 'pivot' index p such that s[p] == '('.
 *    - First, test if s[1] == '('. We do this by checking pairs (1, i) for all i.
 *      If s[1] == '(', then (1, i) forms a regular bracket sequence "()" iff s[i] == ')'.
 *      The query result will be the count of ')' in the tested range. Since s is guaranteed to have at least one ')', 
 *      a non-zero result confirms s[1] == '('.
 *    - If s[1] == ')', we search for a pivot p where s[p] == '(' in the range [2, n].
 *      We use binary search with queries of the form "i 1". Since s[1] == ')', "i 1" forms "()" iff s[i] == '('.
 * 2. Once p is found, determine s[i] for all other indices i using 'weighted' queries.
 *    - We use a property of the query: querying repeated pairs (p, i) allows us to determine if s[i] is ')' or '('.
 *    - Specifically, k copies of (p, i) contribute V(k) = k(k+1)/2 to the total regular substring count if s[i] == ')', and 0 if s[i] == '('.
 *    - By choosing a sequence of counts k_1, k_2, ... such that the subset sums of {V(k_j)} are unique (super-increasing weights),
 *      we can pack multiple indices into a single query and decode which ones are ')' based on the returned sum.
 */

#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// Function to perform a query
// Output format: "0 k i_1 i_2 ... i_k"
// Returns the number of regular bracket substrings
long long ask(const vector<int>& query_indices) {
    if (query_indices.empty()) return 0;
    cout << "0 " << query_indices.size();
    for (int idx : query_indices) {
        cout << " " << idx;
    }
    cout << endl;
    long long res;
    cin >> res;
    if (res == -1) exit(0); // Error or invalid query
    return res;
}

// Calculate V(k) = k*(k+1)/2
long long V(int k) {
    return 1LL * k * (k + 1) / 2;
}

void solve() {
    int n;
    if (!(cin >> n)) return;

    // Step 1: Determine if s[1] is '('
    bool s1_is_open = false;
    
    // We check s[1] against indices 2..n. Due to query length limit of 1000, we split into chunks.
    // Each pair (1, i) takes 2 indices. Max 500 pairs per query.
    vector<int> check_q;
    int limit1 = min(n, 501);
    for (int i = 2; i <= limit1; ++i) {
        check_q.push_back(1);
        check_q.push_back(i);
    }
    
    if (ask(check_q) > 0) {
        s1_is_open = true;
    } else if (n > 501) {
        check_q.clear();
        for (int i = 502; i <= n; ++i) {
            check_q.push_back(1);
            check_q.push_back(i);
        }
        if (ask(check_q) > 0) {
            s1_is_open = true;
        }
    }
    
    int pivot = -1;
    // Pivot must be an index with '('
    
    if (s1_is_open) {
        pivot = 1;
    } else {
        // s[1] is ')'. We need to find a '(' in 2..n.
        // We use binary search. Query "i 1". Since s[1]=')', "i 1" forms "()" only if s[i]=='('.
        int L = 2, R = n;
        while (L < R) {
            int mid = L + (R - L) / 2;
            vector<int> q;
            for (int i = L; i <= mid; ++i) {
                q.push_back(i);
                q.push_back(1);
            }
            if (ask(q) > 0) {
                R = mid;
            } else {
                L = mid + 1;
            }
        }
        pivot = L;
    }

    // Initialize answer string
    string ans_s(n + 1, ' ');
    ans_s[pivot] = '(';
    
    // If we determined s[1] is ')', record it.
    if (!s1_is_open && pivot != 1) {
        ans_s[1] = ')';
    }

    // Collect all unknown indices
    vector<int> unknowns;
    for (int i = 1; i <= n; ++i) {
        if (ans_s[i] == ' ') {
            unknowns.push_back(i);
        }
    }

    if (unknowns.empty()) {
        cout << "1 " << ans_s.substr(1) << endl;
        return;
    }

    // Precompute counts (k) and weights (V(k)) for batch processing.
    // We need unique subset sums. We enforce weight[j+1] > sum(weight[0]...weight[j]).
    vector<int> ks;
    vector<long long> weights;
    long long current_sum = 0;
    int k = 1;
    int total_len = 0;
    
    // Fit as many weighted items as possible into max query length 1000.
    // Each item i with weight k uses 2*k indices in the query string (pairs of (pivot, i)).
    while (true) {
        while (V(k) <= current_sum) {
            k++;
        }
        if (total_len + 2 * k > 1000) break;
        ks.push_back(k);
        weights.push_back(V(k));
        current_sum += V(k);
        total_len += 2 * k;
    }

    int batch_size = ks.size();

    // Process unknowns in batches
    for (size_t i = 0; i < unknowns.size(); i += batch_size) {
        vector<int> batch;
        for (size_t j = 0; j < batch_size && i + j < unknowns.size(); ++j) {
            batch.push_back(unknowns[i + j]);
        }

        // Build query
        vector<int> q;
        for (size_t j = 0; j < batch.size(); ++j) {
            int count = ks[j];
            int u = batch[j];
            for (int rep = 0; rep < count; ++rep) {
                q.push_back(pivot);
                q.push_back(u);
            }
        }

        long long res = ask(q);

        // Decode result using greedy subtraction (possible due to super-increasing weights)
        // Reverse order is crucial
        for (int j = batch.size() - 1; j >= 0; --j) {
            if (res >= weights[j]) {
                ans_s[batch[j]] = ')'; // s[u] is ')'
                res -= weights[j];
            } else {
                ans_s[batch[j]] = '('; // s[u] is '('
            }
        }
    }

    cout << "1 " << ans_s.substr(1) << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}