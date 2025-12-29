#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to send a query
int query(const vector<int>& indices) {
    if (indices.empty()) return 0;
    cout << "0 " << indices.size();
    for (int idx : indices) {
        cout << " " << idx;
    }
    cout << endl; // Flushes output
    int res;
    cin >> res;
    if (res == -1) exit(0); // Exit immediately on invalid query/verdict
    return res;
}

void solve() {
    int n;
    if (!(cin >> n)) return;

    // We need to identify one '(' (u) and one ')' (v) first.
    // We try to assume index 1 is '('. Scan against 2..n.
    int u = -1, v = -1;
    
    vector<int> candidates(n - 1);
    iota(candidates.begin(), candidates.end(), 2); // Candidates 2..n

    bool found = false;
    int batch_size = 500; // Pair (1, k) uses 2 indices. 500 * 2 = 1000 max, which fits in one query.

    // Step 1: Check if index 1 is '('.
    // We form pairs (1, k). If 1 is '(' and k is ')', the pair "()" has score 1.
    // If we get score > 0 for a batch, it means there's at least one ')' in that batch.
    for (int i = 0; i < candidates.size(); i += batch_size) {
        int end = min((int)candidates.size(), i + batch_size);
        vector<int> q_indices;
        for (int k = i; k < end; ++k) {
            q_indices.push_back(1);
            q_indices.push_back(candidates[k]);
        }
        
        int res = query(q_indices);
        if (res > 0) {
            // Found a match. Index 1 is '('. Binary search for ')' in this batch.
            u = 1;
            int l = i, r = end - 1;
            while (l < r) {
                int mid = l + (r - l) / 2;
                vector<int> sub_q;
                for (int k = l; k <= mid; ++k) {
                    sub_q.push_back(1);
                    sub_q.push_back(candidates[k]);
                }
                if (query(sub_q) > 0) {
                    r = mid;
                } else {
                    l = mid + 1;
                }
            }
            v = candidates[l];
            found = true;
            break;
        }
    }

    if (!found) {
        // Index 1 must be ')'. Now search for '(' in candidates.
        // We form pairs (k, 1). If k is '(', "()" has score 1.
        v = 1;
        for (int i = 0; i < candidates.size(); i += batch_size) {
            int end = min((int)candidates.size(), i + batch_size);
            vector<int> q_indices;
            for (int k = i; k < end; ++k) {
                q_indices.push_back(candidates[k]);
                q_indices.push_back(1);
            }
            
            int res = query(q_indices);
            if (res > 0) {
                // Found a match. Binary search for '(' in this batch.
                int l = i, r = end - 1;
                while (l < r) {
                    int mid = l + (r - l) / 2;
                    vector<int> sub_q;
                    for (int k = l; k <= mid; ++k) {
                        sub_q.push_back(candidates[k]);
                        sub_q.push_back(1);
                    }
                    if (query(sub_q) > 0) {
                        r = mid;
                    } else {
                        l = mid + 1;
                    }
                }
                u = candidates[l];
                found = true;
                break;
            }
        }
    }

    string s(n, ' ');
    s[u - 1] = '(';
    s[v - 1] = ')';

    vector<int> unknown;
    for (int i = 1; i <= n; ++i) {
        if (i != u && i != v) {
            unknown.push_back(i);
        }
    }

    // Step 2: Identify remaining indices.
    // We use base-2 weights and padding with two ')' (index v).
    // Each unknown index x is represented as a block "x v v" repeated 2^k times.
    // If x is '(', the block "())" contains one "()" and contributes 1.
    // If x is ')', the block ")))" contributes 0.
    // The sequence "())())" (from two '(' blocks) contributes 1+1 = 2 regular substrings, so counts are additive.
    // We can fit 8 unknowns in one query (sum of lengths = 3 * (2^0 + ... + 2^7) = 3 * 255 = 765 <= 1000).
    int group_size = 8;
    for (int i = 0; i < unknown.size(); i += group_size) {
        int end = min((int)unknown.size(), i + group_size);
        int current_group_size = end - i;
        vector<int> q_indices;
        
        for (int k = 0; k < current_group_size; ++k) {
            int idx = unknown[i + k];
            int count = (1 << k);
            for (int r = 0; r < count; ++r) {
                q_indices.push_back(idx);
                q_indices.push_back(v);
                q_indices.push_back(v);
            }
        }

        int res = query(q_indices);
        
        for (int k = 0; k < current_group_size; ++k) {
            // Check the k-th bit of the result
            if ((res >> k) & 1) {
                s[unknown[i + k] - 1] = '(';
            } else {
                s[unknown[i + k] - 1] = ')';
            }
        }
    }

    cout << "1 " << s << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}