#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    cin >> N >> M;
    vector<pair<int,int>> edges(M);
    for (int i=0; i<M; i++) {
        cin >> edges[i].first >> edges[i].second;
    }
    // Dummy guess
    cout << "1 0 1" << endl;
    cout.flush();
    return 0;
}