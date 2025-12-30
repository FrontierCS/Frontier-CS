#include <iostream>
#include <vector>
using namespace std;

int main() {
    int N, L;
    cin >> N >> L;
    vector<int> T(N);
    for (int i = 0; i < N; ++i) cin >> T[i];
    
    vector<int> count(N, 0);
    vector<int> next_odd(N, -1);
    vector<int> next_even(N, -1);
    
    int cur = 0;
    count[cur] = 1;
    
    for (int week = 2; week <= L; ++week) {
        int i = cur;
        int c = count[i];
        int p = c % 2;  // 0: even, 1: odd
        int j;
        if (p == 1) {  // odd
            if (next_odd[i] != -1) {
                j = next_odd[i];
            } else {
                int best_deficit = -1e9;
                int best_j = -1;
                for (int k = 0; k < N; ++k) {
                    int deficit = T[k] - count[k];
                    if (deficit > best_deficit) {
                        best_deficit = deficit;
                        best_j = k;
                    }
                }
                j = best_j;
                next_odd[i] = j;
            }
        } else {  // even
            if (next_even[i] != -1) {
                j = next_even[i];
            } else {
                int best_deficit = -1e9;
                int best_j = -1;
                for (int k = 0; k < N; ++k) {
                    int deficit = T[k] - count[k];
                    if (deficit > best_deficit) {
                        best_deficit = deficit;
                        best_j = k;
                    }
                }
                j = best_j;
                next_even[i] = j;
            }
        }
        cur = j;
        count[cur]++;
    }
    
    for (int i = 0; i < N; ++i) {
        int a = (next_odd[i] != -1 ? next_odd[i] : 0);
        int b = (next_even[i] != -1 ? next_even[i] : 0);
        cout << a << " " << b << "\n";
    }
    
    return 0;
}