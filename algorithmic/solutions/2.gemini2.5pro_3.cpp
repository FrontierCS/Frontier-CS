#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cstdio>

int n;
std::vector<int> p;

// The function recursively determines the permutation for indices in I,
// knowing the values are from V.
void solve(std::vector<int>& I, std::vector<int>& V) {
    if (I.empty()) {
        return;
    }
    if (I.size() == 1) {
        p[I[0]] = V[0];
        return;
    }

    int m = I.size();
    std::vector<int> I1, I2;
    I1.reserve(m / 2);
    I2.reserve(m - m / 2);

    for (int i = 0; i < m / 2; ++i) {
        I1.push_back(I[i]);
    }
    for (int i = m / 2; i < m; ++i) {
        I2.push_back(I[i]);
    }

    int v0 = V.back();
    V.pop_back();

    std::vector<bool> in_I1(n + 1, false);
    for (int idx : I1) {
        in_I1[idx] = true;
    }

    std::vector<int> ans(V.size());
    long long sum_ans = 0;

    for (size_t i = 0; i < V.size(); ++i) {
        int v = V[i];
        printf("0");
        for (int j = 1; j <= n; ++j) {
            if (in_I1[j]) {
                printf(" %d", v);
            } else {
                printf(" %d", v0);
            }
        }
        printf("\n");
        fflush(stdout);
        scanf("%d", &ans[i]);
        sum_ans += ans[i];
    }
    
    long long N_V = V.size() + 1;
    long long N_I1 = I1.size();
    long long C_I1_v0_num = N_I1 - sum_ans + N_V - 1;
    int C_I1_v0 = C_I1_v0_num / N_V;

    std::vector<int> V1, V2;
    V1.reserve(N_I1);
    V2.reserve(m - N_I1);

    if (C_I1_v0 == 1) {
        V1.push_back(v0);
    } else {
        V2.push_back(v0);
    }

    for (size_t i = 0; i < V.size(); ++i) {
        int v = V[i];
        int C_I1_v = ans[i] - 1 + C_I1_v0;
        if (C_I1_v == 1) {
            V1.push_back(v);
        } else {
            V2.push_back(v);
        }
    }

    solve(I1, V1);
    solve(I2, V2);
}

int main() {
    scanf("%d", &n);
    p.resize(n + 1);

    std::vector<int> initial_I(n), initial_V(n);
    std::iota(initial_I.begin(), initial_I.end(), 1);
    std::iota(initial_V.begin(), initial_V.end(), 1);

    solve(initial_I, initial_V);

    printf("1");
    for (int i = 1; i <= n; ++i) {
        printf(" %d", p[i]);
    }
    printf("\n");
    fflush(stdout);

    return 0;
}