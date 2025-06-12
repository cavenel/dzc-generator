# ---- collect pkg-config information once ---------------------------
VIPSCFLAGS := $(shell pkg-config --cflags vips-cpp)
VIPSLIBS   := $(shell pkg-config --libs   vips-cpp)

# ---- ordinary pattern rules ---------------------------------------
CXX      ?= g++
CXXFLAGS += -std=c++17 $(VIPSCFLAGS)      # or whatever standard you need
LDLIBS   += $(VIPSLIBS)

# one source file → one object file → final executable
build_collection: dzc-generator.o
	$(CXX) $^ $(LDLIBS) -o $@

dzc-generator.o: dzc-generator.c++
	$(CXX) $(CXXFLAGS) -c $<

# ---- house-keeping -------------------------------------------------
.PHONY: clean
clean:
	rm -f build_collection dzc-generator.o