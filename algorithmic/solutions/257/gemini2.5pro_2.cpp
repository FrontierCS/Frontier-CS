#include <iostream>
#include <vector>
#include <utility>

int n;
std::vector<int> ans;

std::pair<int, int> query(int l, int r) {
    if (l > r) {
        return {0, 0};
    }
    std::cout << "? " << l << " " << r << std::endl;
    int x, f;
    std::cin >> x >> f;
    return {x, f};
}

void solve(int l, int r) {
    if (l > r) {
        return;
    }

    auto [x, f] = query(l, r);

    int len = r - l + 1;
    int rem = len - f;

    if (rem == 0) {
        for (int i = l; i <= r; ++i) {
            ans[i] = x;
        }
        return;
    }
    
    int p_len = -1;
    
    auto [x_L, f_L] = query(l, l + rem);
    
    if (x_L == x) {
        p_len = rem - f_L + 1;
    } else {
        auto [x_R, f_R] = query(r - rem, r);
        int q_len = rem - f_R + 1;
        p_len = rem - q_len;
    }

    int s = l + p_len;
    int e = s + f - 1;

    for (int i = s; i <= e; ++i) {
        ans[i] = x;
    }

    solve(l, s - 1);
    solve(e + 1, r);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;
    ans.resize(n + 1);

    solve(1, n);

    std::cout << "! ";
    for (int i = 1; i <= n; ++i) {
        std::cout << ans[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}