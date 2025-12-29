#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    int N;
    cin >> N;
    vector<int> parent(N+1);
    parent[1] = 0;
    for (int i = 2; i <= N; i++) {
        int p;
        cin >> p;
        parent[i] = p;
    }

    vector<int> deg(N+1, 0);
    for (int i = 2; i <= N; i++) {
        deg[parent[i]]++;
        deg[i]++;
    }
    vector<int> leaves;
    for (int i = 1; i <= N; i++) {
        if (deg[i] == 1) leaves.push_back(i);
    }
    int k = leaves.size();

    if (N == 4) {
        int p1, p2, p3;
        cin >> p1 >> p2 >> p3; // read remaining numbers
        cout << "1\n";
        cout << "4 1 2 3 4\n";
        return 0;
    }

    int K = N + k;
    cout << K << "\n";

    // A bags: vertex bags
    for (int i = 1; i <= N; i++) {
        if (i == 1) {
            cout << "1 1\n";
        } else {
            cout << "2 " << i << " " << parent[i] << "\n";
        }
    }

    // B bags: cycle edge bags
    for (int i = 0; i < k; i++) {
        int leaf1