#include <iostream>
#include <vector>
#include <algorithm>
#include <random>

using namespace std;

// Global variables for problem state
int n;
long long k;
int used_queries = 0;
const int MAX_QUERIES = 50000;

long long query(int r, int c) {
    if (used_queries >= MAX_QUERIES) {
        return -1; 
    }
    cout << "QUERY " << r + 1 << " " << c + 1 << endl;
    used_queries++;
    long long val;
    cin >> val;
    return val;
}

void answer(long long ans) {
    cout << "DONE " << ans << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> k)) return 0;

    // Boundary arrays (0-based)
    // L[i]: start column index of candidates in row i
    // R[i]: end column index of candidates in row i
    vector<int> L(n, 0);
    vector<int> R(n, n - 1);
    
    // Rank of elements strictly smaller than the current active region
    long long base_rank = 0;

    // Random number generator
    mt19937_64 rng(1337);

    while (true) {
        // Calculate number of candidates
        long long candidates_count = 0;
        vector<long long> row_cand_count(n);
        for (int i = 0; i < n; ++i) {
            if (L[i] <= R[i]) {
                row_cand_count[i] = (R[i] - L[i] + 1);
                candidates_count += row_cand_count[i];
            } else {
                row_cand_count[i] = 0;
            }
        }

        if (candidates_count == 0) {
            break;
        }

        // If candidates set is small, solve directly
        if (candidates_count <= 850) { 
            vector<long long> values;
            values.reserve(candidates_count);
            for (int i = 0; i < n; ++i) {
                for (int c = L[i]; c <= R[i]; ++c) {
                    values.push_back(query(i, c));
                }
            }
            sort(values.begin(), values.end());
            long long needed = k - base_rank;
            if (needed > 0 && needed <= (long long)values.size()) {
                answer(values[needed - 1]);
            } else {
                answer(values[0]);
            }
            return 0;
        }

        // Pick a random pivot from candidates
        uniform_int_distribution<long long> dist(0, candidates_count - 1);
        long long pick = dist(rng);
        long long current_sum = 0;
        int pivot_r = -1, pivot_c = -1;
        for (int i = 0; i < n; ++i) {
            if (current_sum + row_cand_count[i] > pick) {
                pivot_r = i;
                pivot_c = L[i] + (pick - current_sum);
                break;
            }
            current_sum += row_cand_count[i];
        }

        long long pivot = query(pivot_r, pivot_c);

        long long cnt_less = base_rank; 
        long long cnt_le = base_rank;
        
        vector<int> bound_less(n);
        vector<int> bound_le(n);

        int ptr_le = n - 1;
        long long last_val = -1;
        int last_c = -2;

        for (int i = 0; i < n; ++i) {
            if (i > 0) ptr_le = min(ptr_le, bound_le[i-1]); 
            ptr_le = min(ptr_le, R[i]);
            
            while (ptr_le >= L[i]) {
                long long val = query(i, ptr_le);
                last_val = val;
                last_c = ptr_le;
                if (val <= pivot) break;
                ptr_le--;
            }
            bound_le[i] = ptr_le;
            cnt_le += (ptr_le + 1);

            int ptr_less = ptr_le;
            while (ptr_less >= L[i]) {
                long long val;
                if (ptr_less == last_c) val = last_val;
                else val = query(i, ptr_less);
                
                if (val < pivot) break;
                ptr_less--;
            }
            bound_less[i] = ptr_less;
            cnt_less += (ptr_less + 1);
        }

        if (k <= cnt_less) {
            for (int i = 0; i < n; ++i) {
                R[i] = min(R[i], bound_less[i]);
            }
        } else if (k > cnt_le) {
            base_rank = cnt_le;
            for (int i = 0; i < n; ++i) {
                L[i] = max(L[i], bound_le[i] + 1);
            }
        } else {
            answer(pivot);
            return 0;
        }
    }

    return 0;
}