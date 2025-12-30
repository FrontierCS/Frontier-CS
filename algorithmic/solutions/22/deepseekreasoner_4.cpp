#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    vector<int> parent(N+1);
    for (int i = 1; i <= N-1; i++) {
        int p;
        cin >> p;
        parent[i+1] = p;
    }
    // Identify leaves
    vector<int> deg(N+1,0);
    for (int i = 2; i <= N; i++) {
        deg[parent[i]]++;
        deg[i]++;
    }
    vector<int> leaves;
    for (int i = 1; i <= N; i++) {
        if (deg[i] == 1) leaves.push_back(i);
    }
    int k = leaves.size();
    // Create bags: for each consecutive triple of leaves plus root
    vector<vector<int>> bags;
    for (int i = 0; i < k; i++) {
        int a = leaves[i];
        int b = leaves[(i+1)%k];
        int c = leaves[(i+2)%k];
        bags.push_back({1, a, b, c});
    }
    // Output
    int K = bags.size();
    cout << K << endl;
    for (auto &bag : bags) {
        cout << bag.size();
        for (int x : bag) cout << " " << x;
        cout << endl;
    }
    for (int i = 0; i < K-1; i++) {
        cout << i+1 << " " << i+2 << endl;
    }
    return 0;
}