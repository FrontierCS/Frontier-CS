#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m, T;
    if(!(cin >> n >> m >> T)) return 0;
    for(int i = 0; i < m; ++i){
        int a, b;
        cin >> a >> b;
    }
    
    // Phase 1: no modifications
    cout << 0 << "\n";
    cout.flush();
    
    // Phase 2: trivial guesses (no queries)
    for(int t = 0; t < T; ++t){
        cout << "! " << 1 << "\n";
        cout.flush();
        // We intentionally do not read responses in this placeholder.
        // In a real interactive environment, you would read the verdict here.
    }
    return 0;
}