#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <functional>
#include <cctype>

// Minimal JSON parser for this specific problem
namespace json {
    std::string content;
    size_t pos = 0;

    void load(std::istream& in) {
        content.assign(std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>());
    }

    void skip_whitespace() {
        while (pos < content.length() && isspace(content[pos])) pos++;
    }

    void expect(char c) {
        skip_whitespace();
        if (pos < content.length() && content[pos] == c) {
            pos++;
        }
    }

    std::string parse_string() {
        expect('"');
        size_t start = pos;
        while (pos < content.length() && content[pos] != '"') pos++;
        std::string s = content.substr(start, pos - start);
        pos++;
        return s;
    }

    long long parse_int() {
        skip_whitespace();
        long long val = 0;
        int sign = 1;
        if (pos < content.length() && content[pos] == '-') {
            sign = -1;
            pos++;
        }
        while (pos < content.length() && isdigit(content[pos])) {
            val = val * 10 + (content[pos] - '0');
            pos++;
        }
        return val * sign;
    }

    bool parse_bool() {
        skip_whitespace();
        if (content.substr(pos, 4) == "true") {
            pos += 4;
            return true;
        }
        if (content.substr(pos, 5) == "false") {
            pos += 5;
            return false;
        }
        return false;
    }
}

struct Bin {
    int W, H;
    bool allow_rotate;
};

struct ItemType {
    std::string id;
    int w, h;
    long long v;
    int limit;
};

struct Placement {
    std::string type;
    int x, y, rot;
    long long v;
};

struct CandidateItem {
    std::string id;
    int w, h, rot;
    long long v;
    int original_idx;
};

struct SkylineSegment {
    int x, y, w;
};

Bin bin;
std::vector<ItemType> item_types;

void parse_input() {
    json::load(std::cin);
    json::expect('{');
    json::parse_string(); 
    json::expect(':');
    json::expect('{');
    json::parse_string(); json::expect(':'); bin.W = json::parse_int(); json::expect(',');
    json::parse_string(); json::expect(':'); bin.H = json::parse_int(); json::expect(',');
    json::parse_string(); json::expect(':'); bin.allow_rotate = json::parse_bool();
    json::expect('}');
    json::expect(',');
    json::parse_string(); 
    json::expect(':');
    json::expect('[');
    while (true) {
        json::skip_whitespace();
        if (json::pos >= json::content.length() || json::content[json::pos] == ']') break;
        json::expect('{');
        ItemType it;
        json::parse_string(); json::expect(':'); it.id = json::parse_string(); json::expect(',');
        json::parse_string(); json::expect(':'); it.w = json::parse_int(); json::expect(',');
        json::parse_string(); json::expect(':'); it.h = json::parse_int(); json::expect(',');
        json::parse_string(); json::expect(':'); it.v = json::parse_int(); json::expect(',');
        json::parse_string(); json::expect(':'); it.limit = json::parse_int();
        json::expect('}');
        item_types.push_back(it);
        json::skip_whitespace();
        if (json::pos < json::content.length() && json::content[json::pos] == ',') json::pos++;
        else break;
    }
    json::expect(']');
    json::expect('}');
}


std::vector<Placement> solve(const std::vector<CandidateItem>& candidates) {
    std::vector<Placement> placements;
    std::vector<SkylineSegment> skyline = {{0, 0, bin.W}};
    std::vector<int> remaining_limits(item_types.size());
    for(size_t i = 0; i < item_types.size(); ++i) remaining_limits[i] = item_types[i].limit;

    for (const auto& item : candidates) {
        int w = item.w;
        int h = item.h;

        while (remaining_limits[item.original_idx] > 0) {
            int best_y = bin.H + 1, best_x = -1;

            for (size_t i = 0; i < skyline.size(); ++i) {
                // Try to place on the left of segment i
                int px = skyline[i].x;
                if (px + w <= bin.W) {
                    int py = 0;
                    for (size_t j = 0; j < skyline.size(); ++j) {
                        if (skyline[j].x < px + w && skyline[j].x + skyline[j].w > px) {
                            py = std::max(py, skyline[j].y);
                        }
                    }

                    if (py + h <= bin.H) {
                        if (py < best_y || (py == best_y && px < best_x)) {
                            best_y = py;
                            best_x = px;
                        }
                    }
                }
                
                // Try to place on the right of segment i
                px = skyline[i].x + skyline[i].w - w;
                if (px >= skyline[i].x && px + w <= bin.W) {
                     int py = 0;
                    for (size_t j = 0; j < skyline.size(); ++j) {
                        if (skyline[j].x < px + w && skyline[j].x + skyline[j].w > px) {
                            py = std::max(py, skyline[j].y);
                        }
                    }

                    if (py + h <= bin.H) {
                        if (py < best_y || (py == best_y && px < best_x)) {
                            best_y = py;
                            best_x = px;
                        }
                    }
                }
            }

            if (best_x != -1) {
                placements.push_back({item.id, best_x, best_y, item.rot, item.v});
                remaining_limits[item.original_idx]--;

                int px = best_x;
                int py = best_y;
                std::vector<SkylineSegment> new_skyline;
                new_skyline.push_back({px, py + h, w});
                for (const auto& s : skyline) {
                    if (s.x >= px + w || s.x + s.w <= px) {
                        new_skyline.push_back(s);
                    } else {
                        if (s.x < px) {
                            new_skyline.push_back({s.x, s.y, px - s.x});
                        }
                        if (s.x + s.w > px + w) {
                            new_skyline.push_back({px + w, s.y, s.x + s.w - (px + w)});
                        }
                    }
                }
                
                std::sort(new_skyline.begin(), new_skyline.end(), [](const auto& a, const auto& b){
                    return a.x < b.x;
                });
                
                skyline.clear();
                if (!new_skyline.empty()) {
                    skyline.push_back(new_skyline[0]);
                    for (size_t i = 1; i < new_skyline.size(); ++i) {
                        if (skyline.back().x + skyline.back().w == new_skyline[i].x && skyline.back().y == new_skyline[i].y) {
                            skyline.back().w += new_skyline[i].w;
                        } else if (new_skyline[i].w > 0) {
                            skyline.push_back(new_skyline[i]);
                        }
                    }
                }
            } else {
                break;
            }
        }
    }
    return placements;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    parse_input();

    std::vector<Placement> best_placements;
    long long best_profit = -1;

    std::vector<std::function<bool(const CandidateItem&, const CandidateItem&)>> sorters;
    sorters.push_back([](const CandidateItem& a, const CandidateItem& b) {
        return (double)a.v / ((long long)a.w * a.h) > (double)b.v / ((long long)b.w * b.h);
    });
    sorters.push_back([](const CandidateItem& a, const CandidateItem& b) {
        return (long long)a.w * a.h < (long long)b.w * b.h;
    });
    sorters.push_back([](const CandidateItem& a, const CandidateItem& b) {
        return (long long)a.w * a.h > (long long)b.w * b.h;
    });
    sorters.push_back([](const CandidateItem& a, const CandidateItem& b) {
        int max_a = std::max(a.w, a.h);
        int max_b = std::max(b.w, b.h);
        if (max_a != max_b) return max_a > max_b;
        return std::min(a.w, a.h) > std::min(b.w, b.h);
    });
    sorters.push_back([](const CandidateItem& a, const CandidateItem& b) {
        return (a.w + a.h) > (b.w + b.h);
    });
    sorters.push_back([](const CandidateItem& a, const CandidateItem& b) {
        if (a.h != b.h) return a.h > b.h;
        return a.w > b.w;
    });
    sorters.push_back([](const CandidateItem& a, const CandidateItem& b) {
        if (a.w != b.w) return a.w > b.w;
        return a.h > b.h;
    });

    for (auto& sorter : sorters) {
        std::vector<CandidateItem> candidates;
        for (size_t i = 0; i < item_types.size(); ++i) {
            const auto& it = item_types[i];
            candidates.push_back({it.id, it.w, it.h, 0, it.v, (int)i});
            if (bin.allow_rotate && it.w != it.h) {
                candidates.push_back({it.id, it.h, it.w, 1, it.v, (int)i});
            }
        }

        std::sort(candidates.begin(), candidates.end(), sorter);
        
        std::vector<Placement> current_placements = solve(candidates);
        long long current_profit = 0;
        for (const auto& p : current_placements) {
            current_profit += p.v;
        }

        if (current_profit > best_profit) {
            best_profit = current_profit;
            best_placements = current_placements;
        }
    }

    std::cout << "{\n  \"placements\": [\n";
    for (size_t i = 0; i < best_placements.size(); ++i) {
        const auto& p = best_placements[i];
        std::cout << "    {\"type\":\"" << p.type << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
        if (i < best_placements.size() - 1) {
            std::cout << ",\n";
        } else {
            std::cout << "\n";
        }
    }
    std::cout << "  ]\n}\n";

    return 0;
}