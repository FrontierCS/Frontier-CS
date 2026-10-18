#include <cmath>
#include <algorithm>

// Keep historical scores through 60; above the anchor, compare physical objectives.
static double natural_log_score(long double old_points, long double value,
                                long double anchor, bool minimize) {
    if (minimize && value == 0.0L) return 100.0;
    if (old_points <= 60.0L) return (double)std::max(0.0L, old_points);
    if (!(value > 0.0L) || !(anchor > 0.0L))
        return (double)std::clamp(old_points, 0.0L, 100.0L);
    const long double improvement = minimize
        ? std::log(anchor) - std::log(value)
        : std::log(value) - std::log(anchor);
    return (double)std::clamp(60.0L + improvement, 0.0L, 100.0L);
}

#include "testlib.h"
#include <string>
#include <vector>
#include <cmath>

using namespace std;

// 贪心验证 subsequence (O(N))
bool is_subsequence(const string& text, const string& pattern) {
    if (pattern.empty()) return true;
    int p_idx = 0;
    int p_len = pattern.length();
    
    for (char c : text) {
        if (c == pattern[p_idx]) {
            p_idx++;
            if (p_idx == p_len) return true;
        }
    }
    return false;
}

int main(int argc, char* argv[]) {
    registerTestlibCmd(argc, argv);

    // 1. 读取输入
    string s1 = inf.readLine();
    string s2 = inf.readLine();

    // 2. 读取标准答案 (Generator 生成到 stderr 并重定向到了 answer file)
    // ans 对象读取 .ans 文件
    string z_opt = ans.readString(); 
    double len_opt = (double)z_opt.length();

    // 3. 读取选手输出
    string z_user = ouf.readLine();
    double len_user = (double)z_user.length();

    // 4. 验证选手合法性
    if (!is_subsequence(s1, z_user)) {
        quitf(_wa, "Output is not a subsequence of S1. First mismatch logic check failed.");
    }
    if (!is_subsequence(s2, z_user)) {
        quitf(_wa, "Output is not a subsequence of S2.");
    }

    // A stored common subsequence is a feasible reference, not an upper bound.
    if (len_opt <= 0) quitf(_fail, "Reference subsequence must be nonempty.");
    const double r = len_user / len_opt;
    const double old_ratio = r <= 1.0 ? 0.6 * r : 0.6 + 0.02 * std::log(r);
    const double ratio = natural_log_score(100.0L*old_ratio, len_user, len_opt, false)/100.0;
    quitf(_ok, "User: %.0f, Reference: %.0f, Performance: %.12f, Ratio: %.12f, RatioUnbounded: %.12f",
          len_user, len_opt, r, ratio, ratio);
}
