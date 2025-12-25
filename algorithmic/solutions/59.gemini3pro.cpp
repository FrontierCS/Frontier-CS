#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Function to perform query
char query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    char res;
    cin >> res;
    return res;
}

int n;
vector<int> a;
vector<bool> used;
int h1 = 1, h2 = 2, h3 = 3;
vector<int> val_to_idx;

void update_holes() {
    while (used[h1]) h1++;
    if (h2 <= h1) h2 = h1 + 1;
    while (used[h2]) h2++;
    if (h3 <= h2) h3 = h2 + 1;
    while (used[h3]) h3++;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    a.resize(n + 1, 0);
    used.resize(n + 5, false);
    val_to_idx.resize(n + 5, -1);

    vector<int> buffer;
    int max_filled_val = -1;

    for (int i = 1; i <= n; ++i) {
        update_holes(); // Ensure holes are current

        // If buffer is not empty, we accumulate until we can flush
        if (!buffer.empty()) {
            buffer.push_back(i);
            if (buffer.size() >= 2) {
                // Flush buffer
                stable_sort(buffer.begin(), buffer.end(), [](int x, int y) {
                    return query(x, y) == '<';
                });
                
                for (int idx : buffer) {
                    a[idx] = h1;
                    used[h1] = true;
                    val_to_idx[h1] = idx;
                    if (h1 > max_filled_val) max_filled_val = h1;
                    update_holes();
                }
                buffer.clear();
            }
            continue;
        }

        // Identify representatives
        int rep2 = -1;
        // Check for value in (h1, h2)
        // Since h2 is usually close to h1, we iterate
        for (int v = h1 + 1; v < h2; ++v) {
            if (val_to_idx[v] != -1) {
                rep2 = val_to_idx[v];
                break;
            }
        }
        
        int rep3 = -1;
        if (max_filled_val > h2) {
            rep3 = val_to_idx[max_filled_val];
        }

        int determined_val = -1;

        if (rep2 != -1) {
            char res = query(i, rep2);
            if (res == '<') {
                determined_val = h1;
            } else {
                // > rep2 implies h2 or h3
                if (rep3 != -1) {
                    char res3 = query(i, rep3);
                    if (res3 == '<') {
                        determined_val = h2;
                    } else {
                        determined_val = h3;
                    }
                } else {
                    // Ambiguous between h2 and h3
                    buffer.push_back(i);
                }
            }
        } else {
            // No rep2
            if (rep3 != -1) {
                char res = query(i, rep3);
                if (res == '>') {
                    determined_val = h3;
                } else {
                    // < rep3, so h1 or h2.
                    // rep2 missing means we can't distinguish h1 and h2 easily
                    buffer.push_back(i);
                }
            } else {
                // Neither rep2 nor rep3
                buffer.push_back(i);
            }
        }

        if (determined_val != -1) {
            a[i] = determined_val;
            used[determined_val] = true;
            val_to_idx[determined_val] = i;
            if (determined_val > max_filled_val) max_filled_val = determined_val;
        }
    }

    // Flush remaining buffer
    if (!buffer.empty()) {
        stable_sort(buffer.begin(), buffer.end(), [](int x, int y) {
            return query(x, y) == '<';
        });
        for (int idx : buffer) {
            update_holes();
            a[idx] = h1;
            used[h1] = true;
            val_to_idx[h1] = idx;
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << a[i];
    }
    cout << endl;

    return 0;
}