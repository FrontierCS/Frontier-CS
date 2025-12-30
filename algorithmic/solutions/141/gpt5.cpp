#include <bits/stdc++.h>
using namespace std;

static inline void flush() { cout.flush(); }

char ask(int c) {
    cout << "? " << c << "\n";
    flush();
    char res;
    if (!(cin >> res)) exit(0);
    return res;
}

void reset_mem() {
    cout << "R\n";
    flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, k;
    if (!(cin >> n >> k)) return 0;

    // Base group size
    int base = max(1, k / 2);

    vector<vector<int>> groups;
    vector<int> all(n);
    iota(all.begin(), all.end(), 1);

    // Build initial groups of indices
    for (int i = 0; i < n; i += base) {
        int r = min(n, i + base);
        vector<int> idxs;
        for (int j = i; j < r; ++j) idxs.push_back(all[j]);

        // Determine representatives (first occurrences) within the group
        reset_mem();
        vector<int> reps;
        for (int x : idxs) {
            char ans = ask(x);
            if (ans == 'N') reps.push_back(x);
        }
        groups.push_back(reps);
    }

    // Merge groups pairwise until one remains
    while (groups.size() > 1) {
        vector<vector<int>> next_groups;
        for (size_t i = 0; i < groups.size(); i += 2) {
            if (i + 1 >= groups.size()) {
                next_groups.push_back(groups[i]);
                continue;
            }
            vector<int> A = groups[i];
            vector<int> B = groups[i + 1];

            if (A.empty()) {
                next_groups.push_back(B);
                continue;
            }
            if (B.empty()) {
                next_groups.push_back(A);
                continue;
            }

            vector<int> merged = A;

            // Mark which in B match something in A
            vector<char> matched(B.size(), 0);

            if (k == 1) {
                // Fallback naive method for k == 1
                for (size_t jb = 0; jb < B.size(); ++jb) {
                    bool m = false;
                    for (size_t ia = 0; ia < A.size(); ++ia) {
                        reset_mem();
                        ask(A[ia]);
                        char r = ask(B[jb]);
                        if (r == 'Y') { m = true; break; }
                    }
                    if (!m) merged.push_back(B[jb]);
                }
            } else {
                int chunkA = min((int)A.size(), k / 2);
                if (chunkA <= 0) chunkA = 1;
                // capacity for B in one session
                int capB = max(1, k - chunkA);

                // indices of B that are still unmatched
                vector<int> remainIndices(B.size());
                iota(remainIndices.begin(), remainIndices.end(), 0);

                for (int oA = 0; oA < (int)A.size(); oA += chunkA) {
                    int lenA = min(chunkA, (int)A.size() - oA);
                    int cap = max(1, k - lenA);

                    // Process current unmatched B in segments of size 'cap'
                    for (int pos = 0; pos < (int)remainIndices.size(); pos += cap) {
                        reset_mem();
                        for (int p = 0; p < lenA; ++p) ask(A[oA + p]);

                        for (int t = 0; t < cap && pos + t < (int)remainIndices.size(); ++t) {
                            int j = remainIndices[pos + t];
                            if (matched[j]) continue;
                            char r = ask(B[j]);
                            if (r == 'Y') matched[j] = 1;
                        }
                    }

                    // Shrink remainIndices to those still unmatched
                    vector<int> newRemain;
                    newRemain.reserve(remainIndices.size());
                    for (int id : remainIndices) if (!matched[id]) newRemain.push_back(id);
                    remainIndices.swap(newRemain);
                    if (remainIndices.empty()) break;
                }

                for (size_t jb = 0; jb < B.size(); ++jb) if (!matched[jb]) merged.push_back(B[jb]);
            }

            next_groups.push_back(merged);
        }
        groups.swap(next_groups);
    }

    int d = 0;
    if (!groups.empty()) d = (int)groups[0].size();

    cout << "! " << d << "\n";
    flush();
    return 0;
}