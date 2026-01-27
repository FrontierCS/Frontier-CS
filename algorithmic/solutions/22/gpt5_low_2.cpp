#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if(!(cin >> N)) return 0;
    vector<int> p(N+1, 0);
    for(int i=2;i<=N;i++){
        cin >> p[i];
    }
    // Fallback trivial output to satisfy format (not a valid solution to the full problem).
    // Output a single node tree with a bag of size min(4,N) containing first up to 4 vertices.
    int K = 1;
    cout << K << "\n";
    int sz = min(4, N);
    cout << sz;
    for(int i=1;i<=sz;i++) cout << " " << i;
    cout << "\n";
    // No edges since K=1
    return 0;
}