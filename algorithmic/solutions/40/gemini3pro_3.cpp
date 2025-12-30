#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Function to perform a query
// indices: a vector of indices to include in the query
// The function formats the query as "0 k i_1 ... i_k", prints it, and reads the response.
int ask(const vector<int>& indices) {
    cout << "0 " << indices.size();
    for (int idx : indices) {
        cout << " " << idx;
    }
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0); // Should not happen if solution is correct
    return res;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // ans stores the result string characters (1-based index)
    vector<char> ans(n + 1, 0); 
    bool determined = false;
    char s1_char = 0;
    
    // Divide indices 2..n into chunks of size up to 500.
    // The query limit for length is 1000. Each test pair involves index 1 and index i,
    // so we can fit at most 500 pairs in one query.
    int chunk_size = 500;
    vector<pair<int, int>> chunks;
    for (int i = 2; i <= n; i += chunk_size) {
        chunks.push_back({i, min(n, i + chunk_size - 1)});
    }

    // To store indices that are determined to be the same as s[1] 
    // before we know what s[1] actually is.
    vector<int> same_as_s1;

    for (auto& chunk : chunks) {
        int l = chunk.first;
        int r = chunk.second;
        vector<int> current_indices;
        for (int i = l; i <= r; ++i) current_indices.push_back(i);

        if (!determined) {
            // Strategy to determine s[1]:
            // Try assuming s[1] == '('. Then query "1 i 1 i ..." looks for ')'s.
            // If result > 0, then s[1] is indeed '('.
            // Else, try assuming s[1] == ')'. Query "i 1 i 1 ..." looks for '('s.
            // If result > 0, then s[1] is indeed ')'.
            // If both are 0, then all characters in this chunk are the same as s[1].

            // Check Pattern A: Assume s1 is '(', look for ')'
            vector<int> q_indices;
            for (int idx : current_indices) {
                q_indices.push_back(1);
                q_indices.push_back(idx);
            }
            int resA = ask(q_indices);
            
            if (resA > 0) {
                determined = true;
                s1_char = '(';
                ans[1] = '(';
                // Previous chunks were all same as s1
                for (int idx : same_as_s1) ans[idx] = '(';
                same_as_s1.clear();
            } else {
                // Check Pattern B: Assume s1 is ')', look for '('
                q_indices.clear();
                for (int idx : current_indices) {
                    q_indices.push_back(idx);
                    q_indices.push_back(1);
                }
                int resB = ask(q_indices);
                
                if (resB > 0) {
                    determined = true;
                    s1_char = ')';
                    ans[1] = ')';
                    // Previous chunks were all same as s1
                    for (int idx : same_as_s1) ans[idx] = ')';
                    same_as_s1.clear();
                } else {
                    // Both 0 => all indices in this chunk are same as s1
                    for (int idx : current_indices) same_as_s1.push_back(idx);
                    continue; // Done with this chunk, move to next
                }
            }
        }
        
        // If we reach here, s1_char is determined.
        // We resolve the current chunk using batch queries.
        // Even if we just checked this chunk and found non-zero count, we re-process it
        // to find exact positions using the weighted method.
        
        char target_char = (s1_char == '(' ? ')' : '(');
        char base_char = s1_char;
        
        // Process indices in batches of 8.
        // We use weights 2^0, 2^1, ..., 2^7.
        // Weight w is achieved by repeating the pair w times.
        // Max weight sum for 8 items is 255.
        // Max query length = 2 * 255 = 510 <= 1000.
        for (size_t i = 0; i < current_indices.size(); i += 8) {
            vector<int> batch;
            for (int k = 0; k < 8 && i + k < current_indices.size(); ++k) {
                batch.push_back(current_indices[i + k]);
            }
            
            vector<int> q;
            for (size_t j = 0; j < batch.size(); ++j) {
                int copies = 1 << j;
                for (int c = 0; c < copies; ++c) {
                    if (s1_char == '(') {
                        // Pattern "1 target"
                        q.push_back(1);
                        q.push_back(batch[j]);
                    } else {
                        // Pattern "target 1"
                        q.push_back(batch[j]);
                        q.push_back(1);
                    }
                }
            }
            
            int mask = ask(q);
            for (size_t j = 0; j < batch.size(); ++j) {
                if ((mask >> j) & 1) {
                    ans[batch[j]] = target_char;
                } else {
                    ans[batch[j]] = base_char;
                }
            }
        }
    }
    
    // In case all chunks were homogeneous (impossible by problem statement, but for completeness)
    if (determined) {
        for (int idx : same_as_s1) ans[idx] = s1_char;
    }

    cout << "1 ";
    for (int i = 1; i <= n; ++i) cout << ans[i];
    cout << endl;

    return 0;
}