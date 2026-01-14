#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int do_query(const vector<int>& chameleons) {
    if (chameleons.empty()) {
        return 0;
    }
    cout << "Query " << chameleons.size();
    for (int c : chameleons) {
        cout << " " << c;
    }
    cout << endl;
    int result;
    cin >> result;
    return result;
}

void report_answer(int u, int v) {
    cout << "Answer " << u << " " << v << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N;
    cin >> N;

    vector<int> g;
    vector<bool> is_in_g(2 * N + 1, false);

    // Stage 1: Partitioning into G and H
    for (int i = 1; i <= 2 * N; ++i) {
        if (g.size() == N) {
            break;
        }
        vector<int> current_query_set = g;
        current_query_set.push_back(i);
        if (do_query(current_query_set) == g.size() + 1) {
            g.push_back(i);
        }
    }
    
    for (int chameleon : g) {
        is_in_g[chameleon] = true;
    }

    vector<int> h;
    for (int i = 1; i <= 2 * N; ++i) {
        if (!is_in_g[i]) {
            h.push_back(i);
        }
    }

    // Stage 2: Precompute prefix queries on H
    vector<int> h_prefix_q(N + 1, 0);
    vector<int> h_prefix;
    for (int i = 0; i < N; ++i) {
        h_prefix.push_back(h[i]);
        h_prefix_q[i + 1] = do_query(h_prefix);
    }
    
    // Stage 3: Find partners for each chameleon in G using binary search
    for (int chameleon_g : g) {
        int low = 0, high = N - 1;
        int partner_idx = N - 1;
        
        while (low <= high) {
            int mid = low + (high - low) / 2;
            
            vector<int> query_set;
            for (int i = 0; i <= mid; ++i) {
                query_set.push_back(h[i]);
            }
            int h_sub_q = h_prefix_q[mid + 1];
            
            query_set.push_back(chameleon_g);
            int combined_q = do_query(query_set);

            if (combined_q == h_sub_q) {
                // Partner is in this half or an earlier one
                partner_idx = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }
        report_answer(chameleon_g, h[partner_idx]);
    }

    return 0;
}