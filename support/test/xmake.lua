add_rules("mode.debug", "mode.release")
set_policy("build.c++.gcc.modules.cxx11abi", true)

includes("chimaera.lua")
includes("enable_if.lua")

target("c89/hello")
  add_files("c89/hello.c")
  add_tests("default", {pass_outputs = "Hello, world!\n"})
  chimaera()

target("c23/embed")
  enable_if_c_macro("__has_embed", {languages = "c23"})
  set_languages("c23")
  add_files("c23/embed.c")
  add_tests("default", {pass_outputs = "Hello, world!\n"})
  if is_plat("linux") then on_test(chimaera_run) end

target("c++98/hello")
  add_files("c++98/hello.cc")
  add_tests("default", {pass_outputs = "Hello, world!\n"})
  chimaera()

target("gnu++98/bits-stdc++")
  add_files("gnu++98/bits-stdc++.cc")
  add_tests("default", {pass_outputs = "Hello, world!\n"})
  chimaera()

target("c++23/print")
  enable_if_cxx_header("print")
  set_languages("c++23")
  add_files("c++23/print.cc")
  add_tests("default", {pass_outputs = "Hello, world!\n"})
  chimaera()

target("c++23/import-std")
  enable_if_cxx_feature("__cpp_lib_modules", 202207, {languages = "c++23", cxxflags = {"-fmodules"}})
  set_languages("c++23")
  set_policy("build.c++.modules", true)
  add_files("c++23/import-std.cc")
  add_tests("default", {pass_outputs = "Hello, world!\n"})
  chimaera()
