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
#include <algorithm>
#include <vector>
#include <cmath>

using namespace std;

int main(int argc, char* argv[]) {
    // 初始化 testlib
    registerTestlibCmd(argc, argv);

    // 1. 读取输入数据 (S1, S2)
    string s1 = inf.readToken();
    string s2 = inf.readToken();

    int n = s1.length();
    int m = s2.length();

    // 2. 读取用户输出 (Transcript)
    string t = ouf.readToken();

    // 3. 验证 Transcript 并计算用户的 LCS 长度
    int i = 0; // S1 指针
    int j = 0; // S2 指针

    // 变更点：这里不再累计距离，而是累计匹配长度 (LCS)
    int user_lcs = 0;

    for (size_t k = 0; k < t.length(); k++) {
        char op = t[k];

        if (op == 'M') {
            // Match/Substitute: 消耗 S1 和 S2 各一个字符
            if (i >= n) quitf(_wa, "Invalid transcript: Transcript tries to match but S1 is exhausted at index %d.", i);
            if (j >= m) quitf(_wa, "Invalid transcript: Transcript tries to match but S2 is exhausted at index %d.", j);

            // 变更点：只有当字符真正相等时，LCS 长度才 +1
            // 如果 op 是 'M' 但字符不相等，这在编辑距离中是 Substitute，在 LCS 中不算贡献
            if (s1[i] == s2[j]) {
                user_lcs++;
            }

            i++;
            j++;
        }
        else if (op == 'D') {
            // Delete: 消耗 S1 一个字符，不贡献 LCS
            if (i >= n) quitf(_wa, "Invalid transcript: Transcript tries to delete but S1 is exhausted at index %d.", i);
            i++;
        }
        else if (op == 'I') {
            // Insert: 消耗 S2 一个字符，不贡献 LCS
            if (j >= m) quitf(_wa, "Invalid transcript: Transcript tries to insert but S2 is exhausted at index %d.", j);
            j++;
        }
        else {
            quitf(_wa, "Invalid character '%c' in transcript. Only 'M', 'D', 'I' are allowed.", op);
        }
    }

    // 4. 检查是否完全消耗了 S1 和 S2
    if (i != n) {
        quitf(_wa, "Invalid transcript: S1 was not fully consumed. Ended at %d/%d.", i, n);
    }
    if (j != m) {
        quitf(_wa, "Invalid transcript: S2 was not fully consumed. Ended at %d/%d.", j, m);
    }

    // 5. 读取标准答案中的最优 LCS 长度
    // 变更点：现在 .ans 文件里存的是 LCS 的长度
    int optimal_lcs = ans.readInt();

    // A stored alignment is an empirical performance anchor, not a proof of LCS optimality.
    double ratio;
    if (optimal_lcs == 0) {
        // Zero is exact only when there are no shared characters.
        bool seen[256] = {};
        for (unsigned char c : s1) seen[c] = true;
        bool common = false;
        for (unsigned char c : s2) common |= seen[c];
        if (common) quitf(_fail, "Zero reference with shared characters");
        ratio = 1.0;
    } else {
        double r = (double)user_lcs / optimal_lcs;
        ratio = 0.6 * r;
        ratio = natural_log_score(100.0L * (ratio), user_lcs, optimal_lcs, false) / 100.0;
    }
    quitp(ratio, "User LCS: %d, Reference LCS: %d. Ratio: %.12f, RatioUnbounded: %.12f",
          user_lcs, optimal_lcs, ratio, ratio);
    return 0;
}
