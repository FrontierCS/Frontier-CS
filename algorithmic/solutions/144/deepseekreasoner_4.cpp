#include <bits/stdc++.h>
using namespace std;

typedef pair<int, int> pii;

pii query(const vector<int>& indices) {
    int k = (int)indices.size();
    printf("0 %d", k);
    for (int x : indices) printf(" %d", x);
    printf("\n");
    fflush(stdout);
    int m1, m2;
    scanf("%d %d", &m1, &m2);
    return {m1, m2};
}

int main() {
    int n;
    scanf("%d", &n);
    
    vector<int> all(n);
    iota(all.begin(), all.end(), 1);
    pii global_med = query(all);
    int M1 = global_med.first, M2 = global_med.second;
    
    int a = -1, b = -1;
    // Find two non-median indices on opposite sides
    for (int i = 1; i <= n && a == -1; ++i) {
        for (int j = i + 1; j <= n && a == -1; ++j) {
            vector<int> subset;
            for (int k = 1; k <= n; ++k)
                if (k != i && k != j)
                    subset.push_back(k);
            pii res = query(subset);
            if (res.first == M1 && res.second == M2) {
                a = i;
                b = j;
                break;
            }
        }
    }
    
    vector<int> medians;
    for (int i = 1; i <= n; ++i) {
        if (i == a || i == b) continue;
        
        vector<int> subset1, subset2;
        for (int k = 1; k <= n; ++k) {
            if (k != i && k != a) subset1.push_back(k);
        }
        pii res1 = query(subset1);
        
        for (int k = 1; k <= n; ++k) {
            if (k != i && k != b) subset2.push_back(k);
        }
        pii res2 = query(subset2);
        
        bool not1 = (res1.first != M1 || res1.second != M2);
        bool not2 = (res2.first != M1 || res2.second != M2);
        if (not1 && not2) {
            medians.push_back(i);
        }
    }
    
    printf("1 %d %d\n", medians[0], medians[1]);
    fflush(stdout);
    
    return 0;
}