#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<pair<int,int>> pts(M);
    for (int k = 0; k < M; ++k) {
        int i, j;
        cin >> i >> j;
        pts[k] = {i, j};
    }
    
    const int LIMIT = 2 * N * M;
    vector<pair<char,char>> ops;
    ops.reserve(LIMIT);
    
    auto push = [&](char a, char d) -> bool {
        if ((int)ops.size() >= LIMIT) return false;
        ops.emplace_back(a, d);
        return true;
    };
    
    int r = pts[0].first;
    int c = pts[0].second;
    
    for (int k = 1; k < M; ++k) {
        int tr = pts[k].first;
        int tc = pts[k].second;
        
        // Decide horizontal plan
        int costH0 = abs(tc - c);
        int costHL = 1 + tc;               // Slide to left (0) then move to tc
        int costHR = 1 + (N - 1 - tc);     // Slide to right (N-1) then move to tc
        int hCost = costH0;
        char hChoice = 'N';
        if (costHL < hCost) { hCost = costHL; hChoice = 'L'; }
        if (costHR < hCost) { hCost = costHR; hChoice = 'R'; }
        
        // Decide vertical plan
        int costV0 = abs(tr - r);
        int costVU = 1 + tr;               // Slide to up (0) then move to tr
        int costVD = 1 + (N - 1 - tr);     // Slide to down (N-1) then move to tr
        int vCost = costV0;
        char vChoice = 'N';
        if (costVU < vCost) { vCost = costVU; vChoice = 'U'; }
        if (costVD < vCost) { vCost = costVD; vChoice = 'D'; }
        
        // Perform slides first according to choices
        if (hChoice == 'L') {
            if (!push('S', 'L')) break;
            c = 0;
        } else if (hChoice == 'R') {
            if (!push('S', 'R')) break;
            c = N - 1;
        }
        
        if (vChoice == 'U') {
            if (!push('S', 'U')) break;
            r = 0;
        } else if (vChoice == 'D') {
            if (!push('S', 'D')) break;
            r = N - 1;
        }
        
        // Move vertically to tr
        while (r < tr) {
            if (!push('M', 'D')) goto output;
            ++r;
        }
        while (r > tr) {
            if (!push('M', 'U')) goto output;
            --r;
        }
        // Move horizontally to tc
        while (c < tc) {
            if (!push('M', 'R')) goto output;
            ++c;
        }
        while (c > tc) {
            if (!push('M', 'L')) goto output;
            --c;
        }
    }
    
output:
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    return 0;
}